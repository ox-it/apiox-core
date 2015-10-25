import apiox.api

from ..base import BaseHandler
from apiox.core.response import JSONResponse


class APIListHandler(BaseHandler):
    def get(self, request):
        apis = yield from request.app['api'].list(advertised=True)
        for api in apis:
            api['_links'] = {
                'self': {
                    'href': request.app.router['api:detail'].url(parts={'id': api['id']}),
                }
            }
        data = {
            '_links': {
                'self': {'href': request.app.router['api:list'].url()}
            },
            '_embedded': {
                'api-definition': apis
            }
        }
        return JSONResponse(body=data)
