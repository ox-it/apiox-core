import asyncio
import base64

from aiohttp.web_exceptions import HTTPUnauthorized

from ..models import Principal


@asyncio.coroutine
def basic_auth_middleware(app, handler):
    authentication_scheme = 'Basic realm="{}"'.format(app['auth-realm'])
    if not hasattr(app, 'authentication_schemes'):
        app.authentication_schemes = set()
    app.authentication_schemes.add(authentication_scheme)
    @asyncio.coroutine
    def middleware(request):
        if request.headers.get('Authorization', '').startswith('Basic '):
            try:
                username, password = base64.b64decode(request.headers['Authorization'][6:]).decode('utf-8').split(':', 1)
                principal = Principal.lookup(app, username)
                if principal.is_password_valid(password):
                    request.token = principal.get_token_as_self()
            except (ValueError, IndexError, Principal.DoesNotExist):
                raise HTTPUnauthorized(headers={'WWW-Authenticate': authentication_scheme})
        return (yield from handler(request))
    return middleware
