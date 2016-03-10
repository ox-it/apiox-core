import asyncio
import json

from aiohttp.web_exceptions import HTTPBadRequest, HTTPUnauthorized, HTTPForbidden

from .base import BaseHandler
from .. import db
from ..response import JSONResponse


class TokenRequestHandler(BaseHandler):
    @asyncio.coroutine
    def post(self, request):
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
