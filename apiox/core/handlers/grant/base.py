import asyncio

from aiohttp.web_exceptions import HTTPForbidden, HTTPUnauthorized
from sqlalchemy.orm.exc import NoResultFound

from ..base import BaseHandler
from ... import db
from ...response import JSONResponse

class BaseGrantHandler(BaseHandler):
    @asyncio.coroutine
    def require_oauth2_client(self, request, grant_type=None):
        try:
            yield from self.require_authentication(request)
        except HTTPUnauthorized as e:
            try:
                client_id, client_secret = request.GET['client_id'], request.GET['client_secret']
            except KeyError:
                try:
                    yield from request.post()
                    client_id, client_secret = request.POST['client_id'], request.POST['client_secret']
                except KeyError:
                    raise e
            try:
                client = request.session.query(db.Principal).filter_by(id=client_id).one()
                if not client.is_secret_valid(request.app, client_secret):
                    raise NoResultFound
            except NoResultFound:
                self.oauth2_exception(HTTPUnauthorized, request,
                                      {'error': 'invalid_client'})
            request.token = client.get_token_as_self(request.session)
        if not request.token.client.allowed_oauth2_grant_types:
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'unauthorized_client',
                                   'error_description': "Your client isn't registered as an OAuth2 client."})

        if grant_type and grant_type not in request.token.client.allowed_oauth2_grant_types:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'unauthorized_client',
                                     'error_description': 'The authenticated client is not '
                                         'authorized to use this authorization grant type.'})
    def determine_scopes(self, request):
        scopes = set(request.token.scopes)
        if 'scopes' in request.POST:
            scopes &= set(request.POST['scopes'].split())
        else:
            scopes.discard('/oauth2/client')
            scopes.discard('/oauth2/user')
        return scopes

    def oauth2_exception(self, exception_class, request, body):
        if 'state' in request.POST:
            body['state'] = request.POST['state']
        raise JSONResponse(base=exception_class,
                           body=body)
