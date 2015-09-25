import asyncio
import base64

from aiohttp.web_exceptions import HTTPUnauthorized

from ..db import Principal


@asyncio.coroutine
def basic_auth_middleware(app, handler):
    authentication_scheme = 'Basic realm="{}"'.format(app['auth-realm'])
    if not hasattr(app, 'authentication_schemes'):
        app.authentication_schemes = set()
    app.authentication_schemes.add(authentication_scheme)
    @asyncio.coroutine
    def middleware(request):
        # Don't do any authentication on OPTIONS requests
        if request.method.upper() == 'OPTIONS':
            return (yield from handler(request))

        if request.headers.get('Authorization', '').startswith('Basic '):
            try:
                username, password = base64.b64decode(request.headers['Authorization'][6:]).decode('utf-8').split(':', 1)
                principal = yield from Principal.lookup(app, username)
                if principal and principal.is_secret_valid(password):
                    request.token = yield from principal.get_token_as_self()
            except (ValueError, IndexError):
                raise HTTPUnauthorized(headers={'WWW-Authenticate': authentication_scheme})
        return (yield from handler(request))
    return middleware
