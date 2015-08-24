from .base import BaseHandler
from ..response import JSONResponse

from apiox.core import __version__

class IndexHandler(BaseHandler):
    def __call__(self, request):
        body = {
            'title': 'University of Oxford API',
            'version': __version__,
            '_links': {
                'self': {'href': request.app.router['index'].url()},
                'oauth2:token': {'href': request.app.router['oauth2:token'].url()},
                'oauth2:authorize': {'href': request.app.router['oauth2:authorize'].url()},
            },
        }

        for label, definition in request.app['definitions'].items():
            if label:
                link = definition.copy()
                link.pop('schemas', None)
                link['href'] = request.app.router[label + ':index'].url()
                body['_links']['app:' + label] = link
        
        return JSONResponse(body=body)
