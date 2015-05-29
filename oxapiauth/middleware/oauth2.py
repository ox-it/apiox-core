import asyncio
import datetime
import json

from aiohttp.web_exceptions import HTTPUnauthorized

from ..models import Token

authentication_scheme = 'Bearer realm="api.ox.ac.uk"'

@asyncio.coroutine
def oauth2_middleware(app, handler):
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
                token = Token.objects.get(access_token=bearer_token)
            except Token.DoesNotExist:
                authenticate_header = authentication_scheme \
                    + ', error="invalid_token", error_description="No such token"'
                raise HTTPUnauthorized(body=json.dumps({'error': 'invalid_token',
                                                        'error_description': 'No such token'}).encode(),
                                       headers={'WWW-Authenticate': authenticate_header,
                                                'Content-Type': 'application/json'})
            if token.refresh_at and token.refresh_at <= datetime.datetime.utcnow():
                authenticate_header = authentication_scheme \
                    + ', error="invalid_token", error_description="Token expired"'
                raise HTTPUnauthorized(body=json.dumps({'error': 'invalid_token',
                                                        'error_description': 'Token expired'}).encode(),
                                       headers={'WWW-Authenticate': authenticate_header,
                                                'Content-Type': 'application/json'})
            request.token = token
        return (yield from handler(request))
    return middleware
