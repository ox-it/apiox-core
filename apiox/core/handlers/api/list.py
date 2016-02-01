import asyncio

from apiox.core.db import API
from ..base import BaseHandler
from apiox.core.response import JSONResponse


class APIListHandler(BaseHandler):
    @asyncio.coroutine
    def get(self, request):
        apis = request.session.query(API).filter(API.advertise==True).all()
        return JSONResponse(body={
            '_links': {
                'self': {'href': request.app.router['api:list'].url()}
            },
            '_embedded': {
                'item': [api.to_json(request.app) for api in apis]
            }
        })
