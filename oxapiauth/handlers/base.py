import asyncio

from aiohttp.web_exceptions import HTTPUnauthorized

class BaseHandler(object):

    @asyncio.coroutine
    def require_authentication(self, request):
        if not hasattr(request, 'token'):
            authenticate_header = ', '.join(request.app.authentication_schemes)
            raise HTTPUnauthorized(headers={'WWW-Authenticate': authenticate_header})
