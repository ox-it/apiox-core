import asyncio

from ..models import Principal

@asyncio.coroutine
def remote_user_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        if 'X-Remote-User' in request.headers:
            principal = Principal.lookup(app, request.headers['X-Remote-User'])
            request.token = principal.get_token_as_self(request.app)
        if 'remote_user' in request.GET:
            principal = Principal.lookup(app, request.GET['remote_user'])
            request.token = principal.get_token_as_self(request.app)
        return (yield from handler(request))
    return middleware
