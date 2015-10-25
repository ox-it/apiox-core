import asyncio

from .base import BaseHandler
from ..response import JSONResponse

from apiox.core import __version__


class IndexHandler(BaseHandler):
    @asyncio.coroutine
    def get(self, request):
        body = {
            'title': 'University of Oxford API',
            'version': __version__,
            '_links': {
                'self': {'href': request.app.router['index'].url()},
                'oauth2:token': {'href': request.app.router['oauth2:token'].url()},
                'oauth2:authorize': {'href': request.app.router['oauth2:authorize'].url()},
            },
        }

        for definition in (yield from request.app['api'].list()):
            if definition.get('advertise', True):
                link = {'title': definition['title']}
                try:
                    link['href'] = request.app.router[definition['id'] + ':index'].url()
                except KeyError:
                    logger.warning("API %s has no index handler", definition['id'])
                    continue
                body['_links']['app:' + definition['id']] = link
        
        return JSONResponse(body=body)
