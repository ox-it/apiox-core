import asyncio
import http.client

import aiohttp
import aiohttp.streams
import aiohttp.web
import aiohttp_negotiate

from .base import BaseHandler
from urllib.parse import urljoin

CLIENT_AUTHENTICATION_REQUIRED = 491

class ReverseProxyHandler(BaseHandler):
    discard_request_headers = {'Host',
                               'Authorization',
                               'X-ApiOx-Client',
                               'X-ApiOx-Scopes',
                               'X-ApiOx-Account',
                               'X-ApiOx-Account-Type',
                               'X-ApiOx-User',
                               'X-Forwarded-For',
                               'TE',
                               'Accept-Encoding',
                               'Cookie'}
    discard_response_headers = {'Transfer-Encoding',
                                'Content-Encoding',
                                'Server',
                                'Set-Cookie',
                                'WWW-Authenticate'}

    def __init__(self, app, target, session=None):
        self.target = target
        self.session = session or aiohttp_negotiate.NegotiateClientSession()
        app.register_on_finish(self.close_session)

    def get_target_url(self, request):
        return urljoin(self.target, request.match_info['path'])

    def close_session(self, app):
        self.session.close()

    @asyncio.coroutine
    def __call__(self, request):
        headers = request.headers.copy()
        for header in self.discard_request_headers:
            headers.pop(header.upper(), None)
        headers['X-Request-ID'] = request.context['tags']['request_id']
        
        if getattr(request, 'token', None):
            headers['X-ApiOx-Client'] = request.token.client_id
            headers['X-ApiOx-Scopes'] = ' '.join(scope.id for scope in request.token.scopes)
            headers['X-ApiOx-Account'] = request.token.account_id
            headers['X-ApiOx-Account-Type'] = request.token.account.type.value
            if request.token.user_id and request.token.account.type.value != 'project':
                headers['X-ApiOx-User'] = str(request.token.user_id)

        peername = request.transport.get_extra_info('peername')
        if peername:
            headers['X-Forwarded-For'] = peername[0]
        
        content = request.content
        if isinstance(content, aiohttp.streams.EmptyStreamReader):
            content = None

        try:
            upstream_response = yield from self.session.request(method=request.method,
                                                                params=request.GET,
                                                                allow_redirects=False,
                                                                url=self.get_target_url(request),
                                                                data=content,
                                                                headers=headers)
        except aiohttp.errors.ClientOSError as e:
            raise aiohttp.web.HTTPServiceUnavailable from e
        
        # Can't use 401 here, as that would apply to the request from the
        # reverse-proxy to the proxied service, not from the client to the
        # reverse-proxy. Hence we use a non-standard HTTP status code (491).
        if upstream_response.status == CLIENT_AUTHENTICATION_REQUIRED:
            return (yield from self.require_authentication(request))
        
        headers = upstream_response.headers.copy()
        for header in self.discard_response_headers:
            headers.pop(header.upper(), None)
        response = aiohttp.web.StreamResponse(status=upstream_response.status,
                                              headers=headers)
        response.start(request)
        while True:
            chunk = yield from upstream_response.content.read(4096)
            if not chunk:
                break
            yield from response.write(chunk)
        yield from response.write_eof()
        upstream_response.close()

        return response
