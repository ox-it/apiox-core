import asyncio
import datetime
import http.client
import json


from ... import models
from aiohttp.web import Response

from .base import BaseGrantHandler
from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden

class AuthorizationCodeGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        self.require_oauth2_client(request)
        
        try:
            code = request.POST['code']
        except KeyError:
            self.oauth2_exception(HTTPBadRequest, request,
                                  {'error': 'invalid_request',
                                   'error_description': "Missing `code` parameter"})
        
        try:
            code = models.AuthorizationCode.objects.get(code=code)
        except models.AuthorizationCode.DoesNotExist:
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'Unrecognised authorization code'})

        if code.expire_at < datetime.datetime.utcnow():
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'The authorization code has expired'})

        if code.redirect_uri and code.redirect_uri != request.POST.get('redirect_uri'):
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'Incorrect `redirect_uri` specified'})

        token = code.convert_to_access_token()
        return Response(body=json.dumps(token.as_json(), indent=2).encode(),
                        status=http.client.OK)
