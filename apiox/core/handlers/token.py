import json

from aiohttp.web_exceptions import HTTPBadRequest

from .base import BaseHandler

class TokenRequestHandler(BaseHandler):
    def __init__(self, grant_handlers):
        self.grant_handlers = grant_handlers

    def __call__(self, request):
        yield from request.post()

        try:
            grant_type = request.POST['grant_type']
        except KeyError:
            raise HTTPBadRequest(body=json.dumps({'error': 'invalid_request',
                                                  'error_description': 'Missing grant_type parameter.'}).encode())

        try:
            grant_handler = self.grant_handlers[grant_type]
        except KeyError:
            raise HTTPBadRequest(body=json.dumps({'error': 'unsupported_grant_type',
                                                  'error_description': 'That grant type is not supported.'}).encode())

        return (yield from grant_handler(request))
