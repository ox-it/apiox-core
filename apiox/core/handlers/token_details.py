import asyncio

from .base import BaseHandler
from ..response import JSONResponse

class TokenDetailsHandler(BaseHandler):
    @asyncio.coroutine
    def get(self, request):
        yield from self.require_authentication(request)
        body = {
            '_links': {
                'self': {'href': request.app.router['token-details'].url()},
            },
            'scopes': sorted(scope.id for scope in request.token.scopes),
            '_embedded': {
                'account': {
                    'id': request.token.account_id,
                    'principal': request.token.account.name,
                    'type': request.token.account.type.name,
                },
                'client': {
                    'id': request.token.client.id,
                    'principal': request.token.client.name,
                }
            }
        }
        if getattr(request.token, 'id', None):
            body['id'] = request.token.id
        if request.token.user_id:
            body['_links']['user'] = {
                'href': request.app.router['person:detail'].url(parts={'id': request.token.user_id})
            }
        return JSONResponse(body=body)
