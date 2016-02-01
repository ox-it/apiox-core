import asyncio

from aiohttp.web_exceptions import HTTPForbidden

from apiox.core.db import Principal
from apiox.core.handlers import BaseHandler
from apiox.core.response import JSONResponse

__all__ = ['BaseClientHandler']


class BaseClientHandler(BaseHandler):
    @asyncio.coroutine
    def get_client(self, request, modifying=False):
        client = request.session.query(Principal).filter_by(id=request.match_info['id']).one()
        if modifying and not client.may_administrate(getattr(request, 'token', None)):
            raise JSONResponse(body={'error': 'forbidden',
                                     'error_description': 'You are not an adminsitrator or do not have the required scope to manage clients.'},
                               base=HTTPForbidden)
        return client
