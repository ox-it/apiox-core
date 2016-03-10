import asyncio
from urllib.parse import urljoin
from aiohttp.web_exceptions import HTTPNotFound, HTTPMethodNotAllowed, HTTPServiceUnavailable
import re

from apiox.core import API
from apiox.core.handlers import ReverseProxyHandler


def _first(*values):
    for value in values:
        if value is not None:
            return value

class APIDispatchHandler(ReverseProxyHandler):
    def __init__(self, app):
        super().__init__(app, target=None)

    def get_target_url(self, request):
        url = urljoin(request.api.base,
                      request.api_path['targetPath'].format(*request.api_match.groups(),
                                                            **request.api_match.groupdict()))
        if request.query_string:
            url += '?' + request.query_string
        return url

    @asyncio.coroutine
    def __call__(self, request):
        api_id = request.match_info['api_id']
        api = request.session.query(API).get(api_id)
        if not api:
            raise HTTPNotFound

        for path in api.paths:
            match = re.match(path['sourcePath'], request.match_info['path'])
            if match:
                request.api_path = path
                request.api_match = match
                break
        else:
            raise HTTPNotFound

        available = _first(api.available, path.get('available'), True)
        if not available:
            return HTTPServiceUnavailable

        if 'allowMethods' in path and request.method.upper() not in path['allowMethods']:
            return HTTPMethodNotAllowed(method=request.method.upper(),
                                        allowed_methods=path['allowMethods'])

        require_auth = _first(path.get('requireAuth'), api.require_auth, False)
        require_user = _first(path.get('requireUser'), api.require_user, False)
        require_role = _first(path.get('requireRole'), api.require_role)
        require_scope = _first(path.get('requireScope'), api.require_scope)
        if require_auth:
            yield from self.require_authentication(require_user=require_user,
                                                   require_role=require_role,
                                                   require_scope=require_scope)

        request.api = api

        return (yield from super().__call__(request))
