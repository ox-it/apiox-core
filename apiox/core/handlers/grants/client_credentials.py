import asyncio
import http.client
import json

from ... import models
from aiohttp.web import Response

from .base import BaseGrantHandler

class ClientCredentialsGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        self.require_oauth2_client(request)
        token = models.Token.create_access_token(client=request.token.client,
                                                 account=request.token.client,
                                                 user=None,
                                                 scopes=self.determine_scopes(request),
                                                 expires=True,
                                                 refreshable=False)
        return Response(body=json.dumps(token.as_json(), indent=2).encode(),
                        status=http.client.OK)
