import asyncio

from aiohttp.web_exceptions import HTTPForbidden, HTTPNotFound

from apiox.core.db import API
from apiox.core.response import JSONResponse
from .. import BaseHandler


class APIBaseHandler(BaseHandler):
    @asyncio.coroutine
    def get_api(self, request, modifying=False):
        api = request.session.query(API).get(request.match_info['id'])
        if not api:
            raise HTTPNotFound
        if modifying and not api.may_administrate(getattr(request, 'token', None)):
            raise JSONResponse(body={'error': 'forbidden',
                                     'error_description': 'You are not an adminsitrator or do not have the required scope to manage APIs.'},
                               base=HTTPForbidden)
        return api
