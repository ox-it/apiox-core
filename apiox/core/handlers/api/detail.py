import asyncio
import json

from aiohttp.web_exceptions import HTTPNotFound, HTTPConflict, HTTPNoContent, HTTPForbidden

from ..base import BaseHandler
from apiox.core.response import JSONResponse


class APIDetailHandler(BaseHandler):
    @asyncio.coroutine
    def get(self, request):
        api_id = request.match_info['id']
        try:
            definition = yield from request.app['api'].get(api_id)
        except KeyError:
            raise HTTPNotFound
        else:
            definition['_links'] = {
                'self': {
                    'href': request.app.router['api:detail'].url(parts={'id': definition['id']}),
                }
            }
            return JSONResponse(body=definition)

    @asyncio.coroutine
    def put(self, request):
        api_id = request.match_info['id']
        definition = yield from self.validated_json(request, None, 'api')

        if 'id' in definition and definition['id'] != api_id:
            raise HTTPConflict
        if not all(scope['id'].startswith('/{}/'.format(api_id)) for scope in definition.get('scopes', ())):
            raise HTTPConflict
        if not all(path['sourcePath'].startswith('/{}/'.format(api_id)) for path in definition.get('paths', ())):
            raise HTTPConflict
        if 'localImplementation' in definition:
            raise HTTPForbidden

        yield from request.app['api'].register(api_id, definition)
        return HTTPNoContent()

    @asyncio.coroutine
    def delete(self, request):
        yield from request.app['api'].deregister(request.match_info['id'])
        return HTTPNoContent()

