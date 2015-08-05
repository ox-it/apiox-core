import asyncio
import datetime
import json

from aiohttp.web_exceptions import HTTPUnauthorized

from ..models import Token
from ..response import JSONResponse
from ..token import hash_token

@asyncio.coroutine
def oauth2_middleware(app, handler):
    authentication_scheme = 'Bearer realm="{}"'.format(app['auth-realm'])
    if not hasattr(app, 'authentication_schemes'):
        app.authentication_schemes = set()
    app.authentication_schemes.add(authentication_scheme)
    @asyncio.coroutine
    def middleware(request):
        if request.headers.get('Authorization', '').startswith('Bearer '):
            bearer_token = request.headers['Authorization'][7:]
        elif 'bearer_token' in request.GET:
            bearer_token = request.GET['bearer_token']
        else:
            bearer_token = None
        if bearer_token:
            try:
                token = Token.objects.get(access_token_hash=hash_token(request.app, bearer_token))
            except Token.DoesNotExist:
                authenticate_header = authentication_scheme \
                    + ', error="invalid_token", error_description="No such token"'
                raise JSONResponse(base=HTTPUnauthorized,
                                   body={'error': 'invalid_token',
                                         'error_description': 'No such token'},
                                   headers={'WWW-Authenticate': authenticate_header})
            if token.refresh_at and token.refresh_at <= datetime.datetime.utcnow():
                authenticate_header = authentication_scheme \
                    + ', error="invalid_token", error_description="Token expired"'
                raise JSONResponse(base=HTTPUnauthorized,
                                   body={'error': 'invalid_token',
                                         'error_description': 'Token expired'},
                                   headers={'WWW-Authenticate': authenticate_header})
            request.token = token
        return (yield from handler(request))
    return middleware
