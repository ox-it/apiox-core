import asyncio

from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPUnauthorized, HTTPForbidden, HTTPBadRequest,\
    HTTPMethodNotAllowed
import jsonpointer
import jsonschema

from ..response import JSONResponse

def authentication_scheme_sort_key(scheme):
    scheme = scheme.split(' ', 1)[0]
    return {'Basic': 3,
            'Bearer': 0,
            'Negotiate': 1}.get(scheme, 2)

class BaseHandler(object):
    http_methods = {'get', 'post', 'put', 'delete', 'patch', 'options', 'head'}

    @asyncio.coroutine
    def require_authentication(self, request, *,
                               require_user=False,
                               require_role=None,
                               require_scopes=None,
                               ignore_options=True):
        if ignore_options and request.method.upper() == 'OPTIONS':
            return

        if not hasattr(request, 'token'):
            response = HTTPUnauthorized()
            for scheme in sorted(request.app.authentication_schemes,
                                 key=authentication_scheme_sort_key):
                response.headers.add('WWW-Authenticate', scheme)
            raise response

        if require_user and not request.token.user_id:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'This requires a user.'})

        if require_role and request.token.role not in require_role:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'Wrong principal role. Should be one of {}, not {}'.format(
                                         require_role, request.token.role)})

        if require_scopes:
            missing_scopes = set(require_scopes) - set(scope.id for scope in request.token.scopes)
            if missing_scopes:
                raise JSONResponse(base=HTTPForbidden,
                                   body={'error': 'Requires missing scopes.',
                                         'scopes': sorted(missing_scopes)})

    @asyncio.coroutine
    def validated_json(self, request, app_name, schema_name):
        try:
            body = yield from request.json()
        except ValueError:
            raise HTTPBadRequest
        schema = request.app['schemas'][app_name][schema_name]
        try:
            jsonschema.validate(body, schema)
        except jsonschema.ValidationError as e:
            body = {
                '_links': {
                    'schema': {'href': '/schema/{}/{}'.format(app_name, schema_name)},
                },
            }
            if e.path:
                body['path'] = jsonpointer.JsonPointer.from_parts(e.path).path
            if e.schema_path:
                body['schemaPath'] = jsonpointer.JsonPointer.from_parts(e.schema_path).path
            if e.message:
                body['message'] = e.message
            raise JSONResponse(base=HTTPBadRequest,
                               body=body)
        return body

    @asyncio.coroutine
    def __call__(self, request):
        method = request.method.lower()
        if method not in self.http_methods:
            raise HTTPMethodNotAllowed(method=request.method,
                                       allowed_methods=[m for m in self.http_methods if getattr(self, m, None)])
        try:
            handler = getattr(self, method)
        except AttributeError:
            raise HTTPMethodNotAllowed(method=request.method,
                                       allowed_methods=[m for m in self.http_methods if getattr(self, m, None)])
        return (yield from handler(request))

    @asyncio.coroutine
    def options(self, request):
        return Response(headers={'Allow': ', '.join(m for m in self.http_methods if hasattr(self, m))})
