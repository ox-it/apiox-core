import asyncio
import base64
import gssapi
import socket

from aiohttp.web_exceptions import HTTPUnauthorized

from ..db import Principal

@asyncio.coroutine
def negotiate_auth_middleware(app, handler):
    authentication_scheme = 'Negotiate'
    if not hasattr(app, 'authentication_schemes'):
        app.authentication_schemes = set()
    app.authentication_schemes.add(authentication_scheme)
    @asyncio.coroutine
    def middleware(request):
        # Don't do any authentication on OPTIONS requests
        if request.method.upper() == 'OPTIONS':
            return (yield from handler(request))
        authorization = request.headers.get('Authorization', '')
        if authorization.startswith('Negotiate '):
            host = socket.gethostbyaddr(request.transport.get_extra_info('socket').getsockname()[0])[0]
            service_name = 'HTTP/{}'.format(host)
            service_name = gssapi.Name(service_name)

            # The browser is authenticating using GSSAPI, trim off 'Negotiate ' and decode:
            in_token = base64.b64decode(authorization[10:])

            server_creds = gssapi.Credentials(name=service_name, usage='accept')
            ctx = gssapi.SecurityContext(creds=server_creds)

            # Feed the input token to the context, and get an output token in return
            out_token = ctx.step(in_token)
            if out_token:
                request.negotiate_token = base64.b64encode(out_token).decode()
            if ctx.complete:
                name = str(ctx.initiator_name)
                request.token = Principal.lookup(app, request.session, name=name).get_token_as_self(request.session)
            else:
                raise HTTPUnauthorized
                    
        return (yield from handler(request))
    return middleware

@asyncio.coroutine
def add_negotiate_token(request, response):
    if hasattr(request, 'negotiate_token'):
        response.headers['WWW-Authenticate'] = 'Negotiate {}'.format(request.negotiate_token)

