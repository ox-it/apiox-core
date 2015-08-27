import asyncio

from aiohttp.web_exceptions import HTTPForbidden, HTTPUnauthorized

from ..base import BaseHandler
from ...response import JSONResponse

class BaseGrantHandler(BaseHandler):

    def determine_scopes(self, request):
        scopes = set(request.token.scopes)
        if 'scopes' in request.POST:
            scopes &= set(request.POST['scopes'].split())
        else:
            scopes.discard('/oauth2/client')
            scopes.discard('/oauth2/user')
        return scopes

    def oauth2_exception(self, exception_class, request, body):
        if 'state' in request.POST:
            body['state'] = request.POST['state']
        raise JSONResponse(base=exception_class,
                           body=body)
