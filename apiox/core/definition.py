import os

from aiohttp.web_urldispatcher import UrlDispatcher

def create_grant_handlers():
    from .handlers import grant as grant_handlers
    return {'client_credentials': grant_handlers.ClientCredentialsGrantHandler(),
            'authorization_code': grant_handlers.AuthorizationCodeGrantHandler(),
            'refresh_token': grant_handlers.RefreshTokenGrantHandler()}

def create_router():

    router = UrlDispatcher()

    return router

def hook_in(app):
    from . import handlers
    app['oauth2-grant-handlers'] = create_grant_handlers()

    app['definitions'][None] = {'title': 'University of Oxford API'}
    
    app.router.add_route('GET', '/', handlers.IndexHandler(),
                         name='index')
    app.router.add_route('GET', '/authorize',
                         handlers.AuthorizeHandler().get)
    app.router.add_route('POST', '/authorize',
                         handlers.AuthorizeHandler().post)
    app.router.add_route('POST', '/token',
                         handlers.TokenRequestHandler())

    app.router.add_static('/static', os.path.join(os.path.dirname(__file__), 'static'))

    app['scopes'].add(name='/oauth2/client',
                      title='OAuth2 client',
                      description='Allows a principal to request an OAuth2 token to act on behalf of a user.',
                      available_to_client=True)
    app['scopes'].add(name='/oauth2/user',
                      title='OAuth2 user',
                      description="Allows a user to grant access to a client to act on their behalf.",
                      available_to_client=True)