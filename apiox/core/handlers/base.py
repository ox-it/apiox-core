import asyncio

from aiohttp.web_exceptions import HTTPUnauthorized, HTTPForbidden

from ..response import JSONResponse

def authentication_scheme_sort_key(scheme):
    scheme = scheme.split(' ', 1)[0]
    return {'Basic': 3,
            'Bearer': 0,
            'Negotiate': 1}.get(scheme, 2)

class BaseHandler(object):

    @asyncio.coroutine
    def require_authentication(self, request, *, with_user=False, scopes=()):
        if not hasattr(request, 'token'):
            response = HTTPUnauthorized()
            for scheme in sorted(request.app.authentication_schemes,
                                                   key=authentication_scheme_sort_key):
                response.headers.add('WWW-Authenticate', scheme)
            raise response

        if with_user and not request.token.user:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'This requires a user.'})
        
        missing_scopes = set(scopes) - set(request.token.scopes)
        if missing_scopes:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'Requires missing scopes.',
                                     'scopes': sorted(missing_scopes)})