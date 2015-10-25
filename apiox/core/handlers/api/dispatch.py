import asyncio
from aiohttp.web_exceptions import HTTPNotFound
import re

from apiox.core.handlers import ReverseProxyHandler


class APIDispatchHandler(ReverseProxyHandler):
    def __init__(self):
        super().__init__(self, target=None)

    def get_target(self, request):
        return request.target_url

    @asyncio.coroutine
    def __call__(self, request):
        api_id = request.match_info['api_id']

        try:
            definition = yield from request.app['api'].get(api_id)
        except KeyError as e:
            raise HTTPNotFound from e

        for path in definition.get('paths', ()):
            if not re.match(path['sourcePath'], request.path):
                continue

            require_auth = path.get('requireAuth') or definition.get('requireAuth')
            require_user = path.get('requireUser') or definition.get('requireUser')
            require_role = path.get('requireRole') or definition.get('requireRole')
            require_scope = path.get('requireScope') or definition.get('requireScope')
