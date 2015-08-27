import asyncio
import json

from aiohttp.web_exceptions import HTTPBadRequest, HTTPUnauthorized, HTTPForbidden

from .base import BaseHandler
from .. import db
from ..response import JSONResponse

class TokenRequestHandler(BaseHandler):
    @asyncio.coroutine
    def require_oauth2_client(self, request):
        try:
            self.require_authentication(request)
        except HTTPUnauthorized:
            try:
                client_id, client_secret = request.GET['client_id'], request.GET['client_secret']
            except KeyError:
                try:
                    yield from request.post()
                    client_id, client_secret = request.POST['client_id'], request.POST['client_secret']
                except KeyError:
                    raise
            client = yield from db.Principal.get(request.app, id=client_id)
            if not client or not client.is_secret_valid(client_secret):
                self.oauth2_exception(HTTPUnauthorized, request,
                                      {'error': 'invalid_client'})
            request.token = client.get_token_as_self(request.app)
        if '/oauth2/client' not in request.token.scopes:
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'unauthorized_client',
                                   'error_description': "Your client isn't registered as an OAuth2 client."})

    def __call__(self, request):
        yield from request.post()

        try:
            grant_type = request.POST['grant_type']
        except KeyError:
            raise JSONResponse(base=HTTPBadRequest,
                               body={'error': 'invalid_request',
                                     'error_description': 'Missing grant_type parameter.'})

        try:
            grant_handler = request.app['oauth2-grant-handlers'][grant_type]
        except KeyError:
            raise JSONResponse(base=HTTPBadRequest,
                               body={'error': 'unsupported_grant_type',
                                     'error_description': 'That grant type is not supported.'})

        if grant_type not in request.token.client.allowed_oauth2_grants:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'unauthorized_client',
                                     'error_description': 'The authenticated client is not '
                                         'authorized to use this authorization grant type.'})

        return (yield from grant_handler(request))
