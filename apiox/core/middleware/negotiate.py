import asyncio
import base64
import gssapi

from aiohttp.web_exceptions import HTTPUnauthorized

from ..models import Principal

@asyncio.coroutine
def negotiate_auth_middleware(app, handler):
    authentication_scheme = 'Negotiate'
    if not hasattr(app, 'authentication_schemes'):
        app.authentication_schemes = set()
    app.authentication_schemes.add(authentication_scheme)
    @asyncio.coroutine
    def middleware(request):
        authorization = request.headers.get('Authorization', '')
        if authorization.startswith('Negotiate '):
            service_name = 'HTTP@{}'.format(request.headers.get('Host').split(':')[0])
            service_name = gssapi.Name(service_name, gssapi.C_NT_HOSTBASED_SERVICE)

            # The browser is authenticating using GSSAPI, trim off 'Negotiate ' and decode:
            in_token = base64.b64decode(authorization[10:])

            server_cred = gssapi.Credential(service_name, usage=gssapi.C_ACCEPT)
            ctx = gssapi.AcceptContext(server_cred)

            # Feed the input token to the context, and get an output token in return
            out_token = ctx.step(in_token)
            if out_token:
                request.negotiate_token = base64.b64encode(out_token).decode()
            if ctx.established:
                name = str(ctx.peer_name).split('@')[0]
                request.token = Principal.lookup(app, name).get_token_as_self(request.app)
            else:
                raise HTTPUnauthorized
                    
        return (yield from handler(request))
    return middleware

@asyncio.coroutine
def add_negotiate_token(request, response):
    if hasattr(request, 'negotiate_token'):
        response.headers['WWW-Authenticate'] = 'Negotiate {}'.format(request.negotiate_token)
