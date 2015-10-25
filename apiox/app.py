import asyncio
import functools

import importlib

import aiohttp.web
import aiohttp_jinja2
import aioredis
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


@asyncio.coroutine
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
    import apiox.core.db
    import apiox.api

    app = aiohttp.web.Application(middlewares=middlewares)
    app.on_response_prepare.append(middleware.add_negotiate_token)
    app.on_response_prepare.append(middleware.persist_bearer_token_query_param)
    app.on_response_prepare.append(middleware.add_cors_headers)

    app['definitions'] = {}

    app['orm_mapping'] = {}
    app['register_model'] = functools.partial(apiox.core.db.register_model, app['orm_mapping'])

    app['commands'] = {}
    
    app['api-base'] = api_base
    app['auth-realm'] = auth_realm
    app['default-realm'] = default_realm

    # External services
    app['ldap'] = ldap
    app['db'] = db
    app['grouper'] = grouper
    app['redis'] = yield from aioredis.create_pool(('localhost', 6379))

    app.register_on_finish(lambda app: grouper.close())

    app['token-salt'] = token_salt
    app['api'] = apiox.api.APIManagement(app)

    aiohttp_jinja2.setup(app,
                         loader=jinja2.PackageLoader('apiox.core'),
                         autoescape=True,
                         extensions=['jinja2.ext.autoescape'])
    
    yield from hook_in_apis(app, api_names)
    
    return app

@asyncio.coroutine
def hook_in_apis(app, api_names):
    apis = [importlib.import_module(name) for name in api_names]
    for api in apis:
        if hasattr(api, 'register_services'):
            res = api.register_services(app)
            if (asyncio.iscoroutine(res) or
                    isinstance(res, asyncio.Future)):
                yield from res
        elif not hasattr(api, 'setup'):
            raise AssertionError("{!r} must have at least one of 'hook_in'"
                                 " and 'register_services' as attributes.".format(api))
    for api in apis:
        if hasattr(api, 'setup'):
            res = api.setup(app)
            if (asyncio.iscoroutine(res) or
                    isinstance(res, asyncio.Future)):
                yield from res