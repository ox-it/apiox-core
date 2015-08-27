import asyncio
import datetime

from ... import db
from ...response import JSONResponse

from .base import BaseGrantHandler
from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden
from apiox.core.token import hash_token

class RefreshTokenGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        yield from self.require_oauth2_client(request)
        
        try:
            refresh_token = request.POST['refresh_token']
        except KeyError:
            self.oauth2_exception(HTTPBadRequest, request,
                                  {'error': 'invalid_request',
                                   'error_description': "Missing `refresh_token` parameter"})
        
        refresh_token_hash = hash_token(request.app, refresh_token)
        token = yield from db.Token.get(request.app, refresh_token_hash=refresh_token_hash)
        if not token:
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'Unrecognised refresh token'})

        if token['expire_at'] and token['expire_at'] < datetime.datetime.utcnow():
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'The token has expired'})

        access_token, refresh_token = yield from \
            token.refresh(app=request.app,
                          scopes=request.POST.get('scope', '').split())
        return JSONResponse(body=token.as_json(access_token=access_token,
                                               refresh_token=refresh_token))
