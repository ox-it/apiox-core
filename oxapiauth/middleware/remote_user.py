import asyncio
import base64

from aiohttp.web_exceptions import HTTPUnauthorized

from ..models import Principal

authentication_scheme = 'Basic realm="api.ox.ac.uk"'

@asyncio.coroutine
def remote_user_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        if 'X-Remote-User' in request.headers:
            principal = Principal.lookup(request.headers['X-Remote-User'])
            request.token = principal.get_token_as_self()
        if 'remote_user' in request.GET:
            principal = Principal.lookup(request.GET['remote_user'])
            request.token = principal.get_token_as_self()
        return (yield from handler(request))
    return middleware
