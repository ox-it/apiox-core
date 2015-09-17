import asyncio
import datetime

from sqlalchemy import Column, DateTime, String, ForeignKey, Table, Integer
from sqlalchemy.dialects.postgresql.base import ARRAY

from . import metadata, Model
from .principal import Principal
from ..token import TOKEN_LENGTH, TOKEN_HASH_LENGTH, generate_token, hash_token, TOKEN_LIFETIME

token = Table('token', metadata,
    Column('id', String(TOKEN_LENGTH), primary_key=True),
    Column('access_token_hash', String(TOKEN_HASH_LENGTH)),
    Column('refresh_token_hash', String(TOKEN_HASH_LENGTH), nullable=True),
    
    Column('client_id', None, ForeignKey('principal.id')),
    Column('account_id', None, ForeignKey('principal.id')),
    Column('user_id', Integer),
    
    Column('scopes', ARRAY(String(255))),
    
    Column('granted_at', DateTime()),
    Column('refresh_at', DateTime()),
    Column('expire_at', DateTime(), nullable=True),
)

class Token(Model):
    table = token
    
    def as_json(self, *, access_token=None, refresh_token=None):
        data = {'scopes': sorted(self['scopes']),
                'expires_in': round((self['refresh_at'] - datetime.datetime.utcnow()).total_seconds()),
                'token_type': 'bearer',
                'token_id': self['id']}
        if access_token:
            data['access_token'] = access_token
        if refresh_token:
            data['refresh_token'] = refresh_token
        
        return data

    @asyncio.coroutine
    def set_refresh(self):
        client = yield from Principal.get(self._app, id=self['client_id'])
        if 'refresh_token' not in client.allowed_oauth2_grant_types:
            return None

        self['refresh_at'] = datetime.datetime.utcnow() + datetime.timedelta(0, TOKEN_LIFETIME)

        # Expire scopes that have limited lifetimes
        alive_for = (datetime.datetime.utcnow() - self['granted_at']).total_seconds()
        scopes = [self._app['scopes'][n] for n in self['scopes']]
        scopes = [scope for scope in scopes if not (scope.lifetime and scope.lifetime < alive_for)]
        lifetimes = list(filter(None, (scope.lifetime for scope in scopes)))
        if lifetimes:
            self['refresh_at'] = min(self.refresh_at,
                                     datetime.datetime.utcnow() + datetime.timedelta(seconds=min(lifetimes)))
        self['scopes'] = [scope.name for scope in scopes]

        if self['expire_at'] and self['refresh_at'] > self['expire_at']:
            self['refresh_at'] = self['expire_at']
            refresh_token = None
        else:
            refresh_token = generate_token()
        self['refresh_token_hash'] = hash_token(self._app, refresh_token)
        return refresh_token

    @asyncio.coroutine
    def refresh(self, *, scopes=None):
        if scopes:
            self['scopes'] = list(set(self['scopes']) & set(scopes))
        access_token = generate_token()
        self['access_token_hash'] = hash_token(self._app, access_token)
        refresh_token = yield from self.set_refresh()
        self.save()
        return access_token, refresh_token

    @classmethod
    @asyncio.coroutine
    def create_access_token(cls, *, app, granted_at, client_id, account_id, user_id, scopes, expires=None, refreshable=True):
        if expires is True:
            expires = TOKEN_LIFETIME
        if isinstance(expires, int):
            expires = datetime.datetime.utcnow() + datetime.timedelta(0, expires)
        access_token = generate_token()
        token = cls(app=app,
                    id=generate_token(),
                    access_token_hash=hash_token(app, access_token),
                    client_id=client_id,
                    account_id=account_id,
                    user_id=user_id,
                    scopes=list(scopes),
                    granted_at=granted_at,
                    expire_at=expires)
        refresh_token = yield from token.set_refresh()
        yield from token.insert()
        return token, (access_token, refresh_token)
