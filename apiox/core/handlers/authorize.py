import asyncio
import collections
import datetime
import urllib.parse
from xml.sax.saxutils import escape

from aiohttp_jinja2 import render_template, render_string, APP_KEY

from aiohttp.web_exceptions import HTTPBadRequest, HTTPFound, HTTPForbidden

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
        if '/oauth2/user' not in request.token.scopes:
            self.error_response(HTTPForbidden, request,
                                "Your credentials don't have authority to perform an authorization. You're either using a non-personal SSO account, or have authenticated with an OAuth2 token without the necessary scope.")

        if 'client_id' not in data:
            self.error_response(HTTPBadRequest, request,
                                "No <tt>client_id</tt> parameter provided.")

        client = yield from db.Principal.get(request.app, id=data['client_id'])
        if not client:
            self.error_response(HTTPBadRequest, request,
                                "Couldn't find client")
        
        if 'authorization_code' not in client.allowed_oauth2_grant_types:
            self.error_response(HTTPBadRequest, request,
                                "The client is not allowed to request authorization.")

        try:
            redirect_uri = data['redirect_uri']
        except KeyError:
            self.error_response(HTTPBadRequest, request,
                                'The <tt>redirect_uri</tt> parameter was missing.')
        
        if redirect_uri not in client.redirect_uris:
            self.error_response(HTTPBadRequest, request,
                                'The <tt>redirect_uri</tt> parameter was incorrect.')
        
        scopes = data.get('scope', '').split()
        try:
            scopes = collections.OrderedDict((s, request.app['scopes'][s]) for s in scopes)
        except KeyError as e:
            self.error_response(HTTPBadRequest, request,
                                'Invalid scope: <tt>{}</tt>'.format(escape(e.args[0])))
        permissible_scopes = yield from client.get_permissible_scopes_for_user(request.token.user_id)
        disallowed_scopes = [scope for scope in scopes.values()
                             if scope.name not in permissible_scopes
                                and not scope.requestable_by_all_clients]
        if disallowed_scopes:
            self.error_response(HTTPBadRequest, request,
                                "The client requested scopes it wasn't entitled to ({}).".format(
                                    ', '.join('<tt>{}</tt>'.format(escape(scope.name)) for scope in disallowed_scopes)))
        
        return {'client': client,
                'account': (yield from request.token.account),
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
            authorization_code = db.AuthorizationCode(request.app,
                                                      code_hash=hash_token(request.app, code),
                                                      account_id=request.token.account_id,
                                                      client_id=context['client'].id,
                                                      user_id=request.token.user_id,
                                                      scopes=list(context['scopes'].keys()),
                                                      redirect_uri=context['redirect_uri'],
                                                      granted_at=datetime.datetime.utcnow(),
                                                      expire_at=datetime.datetime.utcnow() + datetime.timedelta(0, 60))
            yield from authorization_code.insert()

            params = {'code': code}
            if context['state']:
                params['state'] = context['state']
            
            redirect_uri = context['redirect_uri'] + '?' + urllib.parse.urlencode(params)
            raise HTTPFound(redirect_uri)
        

    def error_response(self, exception_cls, request, error):
            body = render_string('authorize-error.html', request,
                                 {'error': error}, app_key=APP_KEY)
            raise exception_cls(body=body.encode())
