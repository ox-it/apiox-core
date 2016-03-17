import asyncio
import collections
import datetime
import urllib.parse
from xml.sax.saxutils import escape

from aiohttp_jinja2 import render_template, render_string, APP_KEY

from aiohttp.web_exceptions import HTTPBadRequest, HTTPFound, HTTPForbidden
from sqlalchemy.orm.exc import NoResultFound

from apiox.core.db import Scope
from .. import db
from ..token import generate_token, hash_token, TOKEN_LIFETIME
from .base import BaseHandler

class AuthorizeHandler(BaseHandler):
    @asyncio.coroutine
    def common(self, request):
        yield from self.require_authentication(request)
        data = request.GET if request.method == 'GET' else request.POST

        if not request.token.user_id:
            self.error_response(HTTPForbidden, request,
                                "There is no user associated with the account you logged in with.")
        if not any(scope.id == '/oauth2/user' for scope in request.token.scopes):
            self.error_response(HTTPForbidden, request,
                                "Your credentials don't have authority to perform an authorization. You're either using a non-personal SSO account, or have authenticated with an OAuth2 token without the necessary scope.")

        if 'client_id' not in data:
            self.error_response(HTTPBadRequest, request,
                                "No <tt>client_id</tt> parameter provided.")

        try:
            client = request.session.query(db.Principal).filter_by(id=data['client_id']).one()
        except NoResultFound:
            self.error_response(HTTPBadRequest, request,
                                "Couldn't find client")
        
        if 'authorization_code' not in (client.allowed_oauth2_grant_types or ()):
            self.error_response(HTTPBadRequest, request,
                                "The client is not allowed to request authorization.")

        try:
            redirect_uri = data['redirect_uri']
        except KeyError:
            self.error_response(HTTPBadRequest, request,
                                'The <tt>redirect_uri</tt> parameter was missing.')
        
        if redirect_uri not in (client.redirect_uris or ()):
            self.error_response(HTTPBadRequest, request,
                                'The <tt>redirect_uri</tt> parameter was incorrect.')
        
        scope_ids = data.get('scope', '').split()
        if scope_ids:
            scopes = set(request.session.query(Scope).filter(Scope.id.in_(scope_ids)).all())
        else:
            scopes = set()
        if len(scopes) != len(scope_ids):
            invalid_scopes = set(scope_ids) - set(scope.id for scope in scopes)
            self.error_response(HTTPBadRequest, request,
                                'Invalid scopes: {}'.format(
                                    ', '.join('<tt>{}</tt>'.format(escape(s)) for s in invalid_scopes)))
        permissible_scopes = yield from client.get_permissible_scopes_for_user(request.app,
                                                                               request.session,
                                                                               request.token.user_id,
                                                                               only_implicit=False)
        disallowed_scopes = scopes - permissible_scopes
        if disallowed_scopes:
            self.error_response(HTTPBadRequest, request,
                                "The client requested scopes it wasn't entitled to ({}).".format(
                                    ', '.join('<tt>{}</tt>'.format(escape(scope.id)) for scope in disallowed_scopes)))

        return {'client': client,
                'account': request.token.account,
                'authorize_url': request.app.router['oauth2:authorize'].url(),
                'redirect_uri': redirect_uri,
                'state': data.get('state'),
                'scopes': scopes}

    @asyncio.coroutine
    def get(self, request):
        context = yield from self.common(request)
        
        csrf_token = request.cookies.get('csrf-token') or generate_token()
        
        context.update({'person': request.app['ldap'].get_person(request.token.user_id),
                        'token': request.token,
                        'csrf_token': csrf_token})
        
        response = render_template('authorize.html', request, context)

        if 'csrf-token' not in request.cookies:
            response.set_cookie('csrf-token', csrf_token,
                                httponly=True,
                                secure=(request.scheme=='https'))
        
        return response

    @asyncio.coroutine
    def post(self, request):
        yield from request.post()
        context = yield from self.common(request)

        if 'approve' in request.POST:
            code = generate_token()
            authorization_code = db.AuthorizationCode(code_hash=hash_token(request.app, code),
                                                      account=request.token.account,
                                                      client=context['client'],
                                                      user_id=request.token.user_id,
                                                      scopes=list(context['scopes']),
                                                      redirect_uri=context['redirect_uri'],
                                                      granted_at=datetime.datetime.utcnow(),
                                                      expire_at=datetime.datetime.utcnow() + datetime.timedelta(0, 60))
            request.session.add(authorization_code)

            params = {'code': code}
            if context['state']:
                params['state'] = context['state']
        elif 'reject' in request.POST:
            params = {'error': 'access_denied'}
        else:
            raise HTTPBadRequest
        redirect_uri = context['redirect_uri'] + '?' + urllib.parse.urlencode(params)
        return HTTPFound(redirect_uri)
        

    def error_response(self, exception_cls, request, error):
            body = render_string('authorize-error.html', request,
                                 {'error': error}, app_key=APP_KEY)
            raise exception_cls(body=body.encode())
