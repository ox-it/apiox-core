import asyncio
from urllib.parse import urlparse, parse_qs, urlencode

from ..db import Principal

@asyncio.coroutine
def remote_user_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        if 'X-Remote-User' in request.headers:
            principal = yield from Principal.lookup(app, request.headers['X-Remote-User'])
            if principal:
                request.token = principal.get_token_as_self(request.app)
        if 'remote_user' in request.GET:
            principal = yield from Principal.lookup(app, request.GET['remote_user'])
            if principal:
                request.token = principal.get_token_as_self(request.app)
        return (yield from handler(request))
    return middleware

def persist_remote_user_query_param(request, response):
    if 'remote_user' in request.GET and 'Location' in response.headers:
        parsed = urlparse(response.headers['Location'])
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs['remote_user'] = [request.GET['remote_user']]
        parsed = parsed._replace(query=urlencode(qs, doseq=True))
        response.headers['Location'] = parsed.geturl()

