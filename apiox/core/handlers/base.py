import asyncio

from aiohttp.web_exceptions import HTTPUnauthorized, HTTPForbidden, HTTPBadRequest
import jsonpointer
import jsonschema

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

        if with_user and not request.token.user_id:
            raise JSONResponse(base=HTTPForbidden,
                               body={'error': 'This requires a user.'})
        
        missing_scopes = set(scopes) - set(request.token['scopes'])
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
        schema = request.app['definitions'][app_name]['schemas'][schema_name]
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

