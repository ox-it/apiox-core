import asyncio
import http.client
import json

from ... import db
from ...response import JSONResponse

from .base import BaseGrantHandler

class ClientCredentialsGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        yield from self.require_oauth2_client(request)
        token, (access_token, refresh_token) = yield from \
            db.Token.create_access_token(client=request.token.client,
                                         account=request.token.client,
                                         user=None,
                                         scopes=self.determine_scopes(request),
                                         expires=True,
                                         refreshable=False)
        return JSONResponse(body=token.as_json(access_token=access_token,
                                               refresh_token=refresh_token))
