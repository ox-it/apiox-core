import asyncio
import http.client
import json

from ... import models
from ...response import JSONResponse

from .base import BaseGrantHandler

class ClientCredentialsGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        self.require_oauth2_client(request)
        token, (access_token, refresh_token) = \
            models.Token.create_access_token(client=request.token.client,
                                             account=request.token.client,
                                             user=None,
                                             scopes=self.determine_scopes(request),
                                             expires=True,
                                             refreshable=False)
        return JSONResponse(body=token.as_json(access_token=access_token,
                                               refresh_token=refresh_token))
