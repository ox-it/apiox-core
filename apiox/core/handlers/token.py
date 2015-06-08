import json

from aiohttp.web_exceptions import HTTPBadRequest

from .base import BaseHandler
from ..response import JSONResponse

class TokenRequestHandler(BaseHandler):
    def __call__(self, request):
        yield from request.post()

        try:
            grant_type = request.POST['grant_type']
        except KeyError:
            raise JSONResponse(base=HTTPBadRequest,
                               body={'error': 'invalid_request',
                                     'error_description': 'Missing grant_type parameter.'})

        try:
            grant_handler = request.app['oauth2-grant-handlers'][grant_type]
        except KeyError:
            raise JSONResponse(base=HTTPBadRequest,
                               body={'error': 'unsupported_grant_type',
                                     'error_description': 'That grant type is not supported.'})

        return (yield from grant_handler(request))
