import importlib

import aiohttp.web
import aiohttp_jinja2
import jinja2

from apiox.core import middleware
from apiox.core import scope
from apiox.core.handlers import grant as grant_handlers

default_middlewares = (
    middleware.raven_middleware,
    middleware.request_logging_middleware,
    middleware.negotiate_auth_middleware,
    middleware.basic_auth_middleware,
    middleware.oauth2_middleware
)

default_grant_handler_classes = (
    grant_handlers.AuthorizationCodeGrantHandler,
    grant_handlers.ClientCredentialsGrantHandler,
    grant_handlers.RefreshTokenGrantHandler,
)

def create_app(*,
               api_names,
               middlewares=default_middlewares,
               grant_handler_classes=default_grant_handler_classes,
               api_base,
               default_realm='EXAMPLE.ORG',
               auth_realm='example.org',
               ldap=None,
               db=None,
               grouper=None,
               token_salt=''):
    app = aiohttp.web.Application(middlewares=middlewares)
    app.on_response_start.connect(middleware.add_negotiate_token)
    app.on_response_start.connect(middleware.add_cors_headers)

    app['scopes'] = scope.Scopes()
    app['definitions'] = {}
    
    app['api-base'] = api_base
    app['auth-realm'] = auth_realm
    app['default-realm'] = default_realm

    # External services
    app['ldap'] = ldap
    app['db'] = db
    app['grouper'] = grouper
    
    app['token-salt'] = token_salt

    aiohttp_jinja2.setup(app,
                         loader=jinja2.PackageLoader('apiox.core'),
                         autoescape=True,
                         extensions=['jinja2.ext.autoescape'])
    
    hook_in_apis(app, api_names)
    
    return app

def hook_in_apis(app, api_names):
    apis = [importlib.import_module(name) for name in api_names]
    for api in apis:
        if hasattr(api, 'register_services'):
            api.register_services(app)
        elif not hasattr(api, 'hook_in'):
            raise AssertionError("{!r} must have at least one of 'hook_in'"
                                 " and 'register_services' as attributes.".format(api))
    for api in apis:
        if hasattr(api, 'hook_in'):
            api.hook_in(app)
