import asyncio
import datetime
import json
from urllib.parse import urlparse, parse_qs, urlencode

from aiohttp.web_exceptions import HTTPUnauthorized

from ..db import Token
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
        # Don't do any authentication on OPTIONS requests
        if request.method.upper() == 'OPTIONS':
            return (yield from handler(request))

        if request.headers.get('Authorization', '').startswith('Bearer '):
            bearer_token = request.headers['Authorization'][7:]
        elif 'bearer_token' in request.GET:
            bearer_token = request.GET['bearer_token']
        else:
            bearer_token = None
        if bearer_token:
            token = yield from Token.get(request.app, access_token_hash=hash_token(request.app, bearer_token))
            if not token:
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

def persist_bearer_token_query_param(request, response):
    if 'bearer_token' in request.GET and 'Location' in response.headers:
        parsed = urlparse(response.headers['Location'])
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs['bearer_token'] = [request.GET['bearer_token']]
        parsed = parsed._replace(query=urlencode(qs, doseq=True))
        response.headers['Location'] = parsed.geturl()
