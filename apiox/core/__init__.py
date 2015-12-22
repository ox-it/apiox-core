__version__ = '0.1'

import asyncio
import os

from .schemas import schemas
from .db import API

api_id = 'core'

def _create_grant_handlers():
    from .handlers import grant as grant_handlers
    return {'client_credentials': grant_handlers.ClientCredentialsGrantHandler(),
            'authorization_code': grant_handlers.AuthorizationCodeGrantHandler(),
            'refresh_token': grant_handlers.RefreshTokenGrantHandler()}

@asyncio.coroutine
def setup(app):
    from . import command
    from . import handlers

    app['oauth2-grant-handlers'] = _create_grant_handlers()

    app.router.add_route('*', '/', handlers.IndexHandler(),
                         name='index')
    app.router.add_route('*', '/authorize',
                         handlers.AuthorizeHandler(),
                         name='oauth2:authorize')
    app.router.add_route('*', '/token',
                         handlers.TokenRequestHandler(),
                         name='oauth2:token')

    app.router.add_route('*', '/token/self',
                         handlers.TokenDetailsHandler(),
                         name='token-details')

    app.router.add_route('*', '/api',
                         handlers.api.APIListHandler(),
                         name='api:list')
    app.router.add_route('*', '/api/{id}',
                         handlers.api.APIDetailHandler(),
                         name='api:detail')

    app.router.add_route('*', '/client/self',
                         handlers.client.ClientSelfHandler(),
                         name='client:self')
    app.router.add_route('*', '/client/{id}',
                         handlers.client.ClientDetailHandler(),
                         name='client:detail')
    app.router.add_route('*', '/client/{id}/secret',
                         handlers.client.ClientSecretHandler(),
                         name='client:secret')

    app.router.add_static('/static', os.path.join(os.path.dirname(__file__), 'static'))

    app['commands']['run_server'] = command.run_server
    app['commands']['create_models'] = command.create_models
    app['commands']['shell'] = command.shell
    app['commands']['declare_apis'] = command.declare_apis


def declare_api(session):
    session.merge(API.from_json({
        'id': api_id,
        'title': 'University of Oxford API',
        'description': 'Central API gateway for the University of Oxford',
        'version': __version__,
        'advertise': False,
        'scopes': [{
            'id': '/oauth2/user',
            'title': 'OAuth2 user',
            'description': 'Allows a user to grant access to a client to act on their behalf.',
            'grantedToUser': True,
            'personal': True,
        }]
    }))
