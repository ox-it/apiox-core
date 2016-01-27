import asyncio

from aiohttp.web_exceptions import HTTPNoContent

from apiox.core import api_id
from apiox.core.db import Principal
from apiox.core.handlers import BaseHandler
from apiox.core.response import JSONResponse
from apiox.core.schemas import CLIENT
from apiox.core.token import generate_token, hash_token


class ClientDetailHandler(BaseHandler):
    @asyncio.coroutine
    def get_client(self, request):
        return request.session.query(Principal).filter_by(id=request.match_info['id']).one()

    @asyncio.coroutine
    def get(self, request):
        client = yield from self.get_client(request)
        body = client.to_json()
        body['links'] = {
            'api:secret': {
                'href': request.app.router['client:secret'].url(parts={'id': client.id}),
                'title': 'Generate or remove client secret',
                'description': 'POST to generate a client secret, replacing any existing secret. DELETE to remove any '
                               'existing secret.'
            },
            'self': {
                'href': request.app.router['client:detail'].url(parts={'id': client.id})
            },
        }

        return JSONResponse(
            body=body,
            headers={'Content-Location': body['links']['self']['href']}
        )

    @asyncio.coroutine
    def put(self, request):
        yield from self.require_authentication(request)
        client = yield from self.get_client(request)
        body = yield from self.validated_json(request, api_id, CLIENT)
        client.title = body['title']
        client.description = body['description']
        request.session.add(client)
        return HTTPNoContent()


class ClientSelfHandler(ClientDetailHandler):
    @asyncio.coroutine
    def get_client(self, request):
        yield from self.require_authentication(request)
        print(request.token)
        return request.token.client


class ClientSecretHandler(BaseHandler):
    @asyncio.coroutine
    def get_client(self, request):
        return request.session.query(Principal).filter_by(id=request.match_info['id']).one()

    @asyncio.coroutine
    def post(self, request):
        yield from self.require_authentication(request)
        client = yield from self.get_client(request)
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
        client = yield from self.get_client(request)
        client.secret_hash = None
        request.session.add(client)
        return HTTPNoContent()