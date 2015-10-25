import asyncio
import json


class APIManagement(object):
    def __init__(self, app):
        self.app = app
        self.redis = app['redis']

    @asyncio.coroutine
    def get(self, api_id):
        with (yield from self.redis) as redis:
            data = yield from redis.hget('api', api_id)
        if data is None:
            raise KeyError(api_id)
        return json.loads(data.decode())

    @asyncio.coroutine
    def list(self, *, advertised=None):
        with (yield from self.redis) as redis:
            apis = yield from redis.hgetall('api')

        apis = [json.loads(v.decode()) for v in apis.values()]
        if advertised is True:
            apis = [api for api in apis if api.get('advertise', True)]
        elif advertised is False:
            apis = [api for api in apis if not api.get('advertise', True)]

        return apis

    @asyncio.coroutine
    def register(self, api_id, definition, *,
                 deregister_on_finish=False):
        definition['id'] = api_id
        with (yield from self.redis) as redis:
            current_data = yield from redis.hget('api', api_id)
            if current_data:
                current_data = json.loads(current_data.decode())
                current_scope_ids = set(s['id'] for s in current_data.get('scopes', ()))
                new_scope_ids = set(s['id'] for s in definition.get('scopes', ()))
                removed_scope_ids = current_scope_ids - new_scope_ids
                if removed_scope_ids:
                    yield from redis.hdel('scope', removed_scope_ids)
            yield from redis.hset('api', api_id, json.dumps(definition).encode())
            scopes = []
            for scope in definition.get('scopes', ()):
                scopes.extend((scope['id'], json.dumps(scope).encode()))
            if scopes:
                yield from redis.hmset('scope', *scopes)

        if deregister_on_finish:
            self.app.register_on_finish(lambda app: self.deregister(api_id))

    @asyncio.coroutine
    def deregister(self, api_id):
        with (yield from self.redis) as redis:
            current_data = yield from redis.hget('api', api_id)
            if current_data:
                current_data = json.loads(current_data.decode())
                current_scope_ids = set(s['id'] for s in current_data.get('scopes', ()))
                if current_scope_ids:
                    yield from redis.hdel('scope', current_scope_ids)
            yield from redis.hdel('api', api_id)
