import asyncio
from sqlalchemy import Table, Column, String, Integer, DateTime, ForeignKey

from . import metadata, Instance
from apiox.core.token import TOKEN_HASH_LENGTH, TOKEN_LENGTH
from sqlalchemy.dialects.postgresql import ARRAY

from .token import Token

__all__ = ['authorization_code', 'AuthorizationCode']

authorization_code = Table('authorization_code', metadata,
    Column('code_hash', String(TOKEN_HASH_LENGTH), primary_key=True),

    Column('client_id', String(TOKEN_LENGTH), ForeignKey('principal.id')),
    Column('account_id', String(TOKEN_LENGTH), ForeignKey('principal.id')),
    Column('user_id', Integer),
    Column('scopes', ARRAY(String)),
    Column('redirect_uri', String),
    
    Column('granted_at', DateTime()),
    Column('expire_at', DateTime()),
    Column('token_expire_at', DateTime(), nullable=True),
    
)

class AuthorizationCode(Instance):
    table = authorization_code

    @asyncio.coroutine
    def convert_to_access_token(self):
        yield from self.delete()
        return (yield from Token.create_access_token(app=self._app,
                                                     client_id=self.client_id,
                                                     account_id=self.account_id,
                                                     user_id=self.user_id,
                                                     scopes=self['scopes'],
                                                     granted_at=self['granted_at'],
                                                     expires=self['token_expire_at']))
