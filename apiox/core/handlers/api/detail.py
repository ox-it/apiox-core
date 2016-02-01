import asyncio

from aiohttp.web_exceptions import HTTPNotFound, HTTPConflict, HTTPNoContent, HTTPForbidden

from apiox.core.db import API
from . import APIBaseHandler
from ..base import BaseHandler
from apiox.core.response import JSONResponse


class APIDetailHandler(APIBaseHandler):
    @asyncio.coroutine
    def get(self, request):
        api = self.get_api(request)
        return JSONResponse(body=api.to_json(request.app,
                                             may_administrate=api.may_administrate(getattr(request, 'token', None))))

    @asyncio.coroutine
    def put(self, request):
        api = self.get_api(request, modifying=True)
        if not api:
            api = API(id=request.match_info['id'])
        definition = yield from self.validated_json(request, None, 'api')

        if 'id' in definition and definition['id'] != api.id:
            raise HTTPConflict
        if not all(scope['id'].startswith('/{}/'.format(api,id)) for scope in definition.get('scopes', ())):
            raise HTTPConflict
        if not all(path['sourcePath'].startswith('/{}/'.format(api.id)) for path in definition.get('paths', ())):
            raise HTTPConflict
        if 'localImplementation' in definition:
            raise HTTPForbidden

        request.session.merge(api)
        return HTTPNoContent()

    @asyncio.coroutine
    def delete(self, request):
        api = self.get_api(request, modifying=True)
        if not api:
            raise HTTPNotFound
        request.session.delete(api)
        return HTTPNoContent()
