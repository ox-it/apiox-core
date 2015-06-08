import asyncio
import datetime

from ... import models
from ...response import JSONResponse

from .base import BaseGrantHandler
from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden

class RefreshTokenGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        self.require_oauth2_client(request)
        
        try:
            refresh_token = request.POST['refresh_token']
        except KeyError:
            self.oauth2_exception(HTTPBadRequest, request,
                                  {'error': 'invalid_request',
                                   'error_description': "Missing `refresh_token` parameter"})
        
        try:
            token = models.Token.objects.get(refresh_token=refresh_token)
        except models.Token.DoesNotExist:
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'Unrecognised refresh token'})

        if token.expire_at and token.expire_at < datetime.datetime.utcnow():
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'The token has expired'})

        token.refresh(request.POST.get('scope', '').split())
        return JSONResponse(body=token.as_json())
