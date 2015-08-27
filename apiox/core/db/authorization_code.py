import asyncio
from sqlalchemy import Table, Column, String, Integer, DateTime

from . import metadata, Instance
from apiox.core.token import TOKEN_HASH_LENGTH, TOKEN_LENGTH
from sqlalchemy.dialects.postgresql import ARRAY

from .token import Token

__all__ = ['authorization_code', 'AuthorizationCode']

authorization_code = Table('apiox_authorization_code', metadata,
    Column('code_hash', String(TOKEN_HASH_LENGTH), primary_key=True),

    Column('client_id', String(TOKEN_LENGTH)),
    Column('account_id', String(TOKEN_LENGTH)),
    Column('user_id', Integer),
    Column('scopes', ARRAY(String)),
    Column('redirect_uri', String),
    
    Column('granted_at', DateTime(True)),
    Column('expire_at', DateTime(True)),
    Column('token_expire_at', DateTime(True), nullable=True),
    
)

class AuthorizationCode(Instance):
    table = authorization_code

    @staticmethod
    @asyncio.coroutine
    def get(cls, app, **kwargs):
        stmt = select([cls.table]).where(*[getattr(cls.table.c, k) == kwargs[k] for k in kwargs])
        res = yield app['db'].execute(stmt)
        return (yield from res.first())

    @asyncio.coroutine
    def delete(self, app):
        pks = self.table.primary_key.columns.keys()
        stmt = self.table.delete().where(*[getattr(self.table.c, pk) == self[pk] for pk in pks])
        yield from app['db'].execute(stmt)

    @asyncio.coroutine
    def convert_to_access_token(self, app):
        stmt = authorization_code.delete() \
            .where(authorization_code.c.code_hash == self['code_hash'])
        yield from self.delete(app)
        return (yield from Token.create_access_token(app=app,
                                                     client=self['client'],
                                                     account=self['account'],
                                                     user_id=self['user_id'],
                                                     scopes=self['scopes'],
                                                     granted_at=self['granted_at'],
                                                     expires=self['token_expire_at']))
