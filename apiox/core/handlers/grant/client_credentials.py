import asyncio
import http.client
import json

from ... import db
from ...response import JSONResponse

from .base import BaseGrantHandler

class ClientCredentialsGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        yield from self.require_oauth2_client(request, grant_type='client_credentials')
        token, (access_token, refresh_token) = yield from \
            db.Token.create_access_token(client_id=request.token.client_id,
                                         account_id=request.token.client_id,
                                         user=None,
                                         scopes=self.determine_scopes(request),
                                         expires=True,
                                         refreshable=False)
        return JSONResponse(body=token.as_json(access_token=access_token,
                                               refresh_token=refresh_token))
