import asyncio
import functools
import os.path

import aiohttp
import aiohttp.web
import aiohttp_jinja2
import django
import jinja2

from .handlers import *
from .handlers.grants import *
from . import middleware
from .scope import Scopes
#from oxapiauth.handlers.reverse_proxy import ReverseProxyHandler

if __name__ == "__main__":
    django.setup()

    grant_handlers = {'client_credentials': ClientCredentialsGrantHandler(),
                      'authorization_code': AuthorizationCodeGrantHandler()}
    
    app = aiohttp.web.Application(middlewares=[middleware.basic_auth_middleware,
                                               middleware.oauth2_middleware,
                                               middleware.remote_user_middleware])
    app['scopes'] = Scopes('../ox-api-auth-config/scopes.yml')

    aiohttp_jinja2.setup(app,
                         loader=jinja2.PackageLoader('oxapiauth'),
                         autoescape=True,
                         extensions=['jinja2.ext.autoescape'])

    app.router.add_route('GET', '/authorize', AuthorizeHandler().get)
    app.router.add_route('POST', '/authorize', AuthorizeHandler().post)
    app.router.add_route('POST', '/token', TokenRequestHandler(grant_handlers))
    app.router.add_route('*', r'/library/{path:.*}', ReverseProxyHandler('http://api.m.ox.ac.uk/library/'))

    app.router.add_static('/static', os.path.join(os.path.dirname(__file__), 'static'))
    
    loop = asyncio.get_event_loop()
    f = loop.create_server(app.make_handler(), 'localhost', 8080)
    srv = loop.run_until_complete(f)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass