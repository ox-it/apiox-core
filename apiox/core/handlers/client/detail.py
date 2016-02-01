import asyncio

from aiohttp.web_exceptions import HTTPNoContent, HTTPForbidden
from apiox.core import api_id
from apiox.core.db import Principal
from apiox.core.handlers import BaseHandler
from apiox.core.handlers.client.base import BaseClientHandler
from apiox.core.response import JSONResponse
from apiox.core.schemas import CLIENT
from apiox.core.token import generate_token, hash_token

__all__ = ['ClientSelfHandler', 'ClientDetailHandler', 'ClientSecretHandler']


class ClientSelfHandler(BaseClientHandler):
    @asyncio.coroutine
    def __call__(self, request):
        yield from self.require_authentication(request)
        request.match_info['id'] = request.token.client_id
        return (yield from request.app.router['client:detail'].handler(request))


class ClientDetailHandler(BaseClientHandler):
    @asyncio.coroutine
    def get(self, request):
        yield from self.require_authentication(request)
        client = yield from self.get_client(request)
        may_administrate = client.may_administrate(getattr(request, 'token', None))
        print(may_administrate)
        body = client.to_json(request.app, may_administrate=may_administrate)

        return JSONResponse(
            body=body,
            headers={'Content-Location': body['_links']['self']['href']}
        )

    @asyncio.coroutine
    def put(self, request):
        yield from self.require_authentication(request)
        client = yield from self.get_client(request, modifying=True)
        body = yield from self.validated_json(request, api_id, CLIENT)
        client.title = body.get('title')
        client.description = body.get('description')
        client.redirect_uris = body.get('redirectURIs', [])
        client.allowed_oauth2_grant_types = body.get('oauth2GrantTypes', [])
        request.session.add(client)
        return HTTPNoContent()


class ClientSecretHandler(BaseClientHandler):
    @asyncio.coroutine
    def post(self, request):
        yield from self.require_authentication(request)
        client = yield from self.get_client(request, modifying=True)
        secret = generate_token()
        client.secret_hash = hash_token(request.app, secret)
        request.session.add(client)
        return JSONResponse(
            body={'secret': secret},
            headers={'Pragma': 'no-cache'},
        )

    @asyncio.coroutine
    def delete(self, request):
        yield from self.require_authentication(request)
        client = yield from self.get_client(request, modifying=True)
        client.secret_hash = None
        request.session.add(client)
        return HTTPNoContent()