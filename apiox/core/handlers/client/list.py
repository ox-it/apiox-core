import asyncio

from aiohttp.web_exceptions import HTTPCreated

from apiox.core.db import Principal
from apiox.core.handlers.client import BaseClientHandler
from apiox.core.response import JSONResponse
from apiox.core.token import generate_token

__all__ = ['ClientListHandler']


class ClientListHandler(BaseClientHandler):
    @asyncio.coroutine
    def get(self, request):
        yield from self.require_authentication(request, require_scopes={'/oauth2/manage-client'})
        body = {
            '_embedded': {
                'item': [p.to_json(request.app, True) for p in request.token.account.administrator_of],
            },
        },
        return JSONResponse(body=body)

    @asyncio.coroutine
    def post(self, request):
        yield from self.require_authentication(request, require_scopes={'/oauth2/manage-client'})
        client = Principal(id=generate_token())
        client.administrators = [request.token.account]
        request.session.add(client)
        return HTTPCreated(headers={'Location': request.app.router['client:detail'].url(parts={'id': client.id})})