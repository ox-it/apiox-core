import asyncio

from apiox.core.handlers.client import BaseClientHandler
from apiox.core.response import JSONResponse

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
