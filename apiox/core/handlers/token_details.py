import asyncio

from .base import BaseHandler
from ..response import JSONResponse

class TokenDetailsHandler(BaseHandler):
    @asyncio.coroutine
    def get(self, request):
        yield from self.require_authentication(request)
        account = yield from request.token.account
        client = yield from request.token.client
        body = {
            '_links': {
                'self': {'href': request.app.router['token-details'].url()},
            },
            'scopes': sorted(request.token.scopes),
            '_embedded': {
                'account': {
                    'id': account.id,
                    'principal': account.name,
                    'type': account.type.name,
                },
                'client': {
                    'id': client.id,
                    'principal': client.name,
                }
            }
        }
        if request.token.user_id:
            body['_links']['user'] = {
                'href': request.app.router['person:detail'].url(parts={'id': request.token.user_id})
            }
        return JSONResponse(body=body)
