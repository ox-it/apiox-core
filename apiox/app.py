import asyncio
import contextlib

import functools

import importlib

import aiohttp.web
import aiohttp_jinja2
import aioredis
import jinja2
from sqlalchemy.orm import sessionmaker

from apiox.core import middleware
from apiox.core.handlers import grant as grant_handlers

default_middlewares = (
    middleware.db_session,
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


def session_context(app):
    Session = sessionmaker(bind=app['db'])
    @contextlib.contextmanager
    def cm():
        session = Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
    return cm


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

    app = aiohttp.web.Application(middlewares=middlewares)
    app.on_response_prepare.append(middleware.add_negotiate_token)
    app.on_response_prepare.append(middleware.persist_bearer_token_query_param)
    app.on_response_prepare.append(middleware.add_cors_headers)

    app['schemas'] = {}
    app['commands'] = {}
    
    app['api-base'] = api_base
    app['auth-realm'] = auth_realm
    app['default-realm'] = default_realm

    # External services
    app['ldap'] = ldap
    app['db'] = db
    app['db-session'] = session_context(app)
    app['grouper'] = grouper

    app.register_on_finish(lambda app: grouper.close())

    app['token-salt'] = token_salt

    aiohttp_jinja2.setup(app,
                         loader=jinja2.PackageLoader('apiox.core'),
                         autoescape=True,
                         extensions=['jinja2.ext.autoescape'])

    app['apis'] = [importlib.import_module(name) for name in api_names]

    yield from setup_apis(app)

    from .core import handlers
    app.router.add_route('*', '/{api_id}/{path:.*}',
                         handlers.api.APIDispatchHandler(app),
                         name='api:dispatch')

    return app


@asyncio.coroutine
def setup_apis(app):
    for api in app['apis']:
        if hasattr(api, 'register_services'):
            res = api.register_services(app)
            if (asyncio.iscoroutine(res) or
                    isinstance(res, asyncio.Future)):
                yield from res
        elif not (hasattr(api, 'setup') or hasattr(api, 'declare_api')):
            raise AssertionError("{!r} must have at least one of 'hook_in'"
                                 " and 'register_services' as attributes.".format(api))
    for api in app['apis']:
        if hasattr(api, 'setup'):
            res = api.setup(app)
            if (asyncio.iscoroutine(res) or
                    isinstance(res, asyncio.Future)):
                yield from res