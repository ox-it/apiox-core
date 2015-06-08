import asyncio

from aiohttp.web_exceptions import HTTPUnauthorized, HTTPForbidden

from ..response import JSONResponse

class BaseHandler(object):

    @asyncio.coroutine
    def require_authentication(self, request, *, with_user=False, scopes=()):
        if not hasattr(request, 'token'):
            authenticate_header = ', '.join(request.app.authentication_schemes)
            raise HTTPUnauthorized(headers={'WWW-Authenticate': authenticate_header})

        if with_user and not request.token.user:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'This requires a user.'})
        
        missing_scopes = set(scopes) - set(request.token.scopes)
        if missing_scopes:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'Requires missing scopes.',
                                     'scopes': sorted(missing_scopes)})