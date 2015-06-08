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
            },
        }

        for label, definition in request.app['definitions'].items():
            if label:
                body['_links']['app:' + label] = {
                    'href': request.app.router[label + ':index'].url(),
                    'title': definition['title'],
                    'version': definition['version'],
                } 
        
        return JSONResponse(body=body)