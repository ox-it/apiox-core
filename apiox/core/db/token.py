import asyncio
import datetime

import collections
from aiohttp.web_exceptions import HTTPUnauthorized
from sqlalchemy import Column, DateTime, String, ForeignKey, Table, Integer
from sqlalchemy.dialects.postgresql.base import ARRAY
from sqlalchemy.orm import relationship

from apiox.core.response import JSONResponse
from . import Base
from .principal import Principal
from ..token import TOKEN_LENGTH, TOKEN_HASH_LENGTH, generate_token, hash_token, TOKEN_LIFETIME

__all__ = ['Token', 'EphemeralToken']

token_scope = Table('token_scope', Base.metadata,
    Column('scope_id', String, ForeignKey('scope.id'), primary_key=True),
    Column('token_id', String(TOKEN_LENGTH), ForeignKey('token.id'), primary_key=True),
)

class Token(Base):
    __tablename__ = 'token'

    class Error(Exception): pass

    class Expired(Error):
        description = 'Token expired.'

    class NotFound(Error):
        description = 'Token not found.'

    class Overused(Error):
        description = 'The token has been used its allotted number of times.'

    id = Column(String(TOKEN_LENGTH), primary_key=True)
    access_token_hash = Column(String(TOKEN_HASH_LENGTH))
    refresh_token_hash = Column(String(TOKEN_HASH_LENGTH), nullable=True)
    
    client_id = Column(String, ForeignKey('principal.id'))
    account_id = Column(String, ForeignKey('principal.id'))
    user_id = Column(Integer)

    scopes = relationship('Scope', secondary=token_scope, backref='tokens')

    granted_at = Column(DateTime())
    refresh_at = Column(DateTime())
    expire_at = Column(DateTime(), nullable=True)

    remaining_uses = Column(Integer, nullable=True)

    client = relationship('Principal', foreign_keys=[client_id])
    account = relationship('Principal', foreign_keys=[account_id])

    parent_id = Column(String(TOKEN_LENGTH), ForeignKey('token.id'), nullable=True)
    parent = relationship('Token', backref='children', remote_side=id)

    def to_json(self, *, access_token=None, refresh_token=None):
        data = {'scopes': sorted(scope.id for scope in self.scopes),
                'expires_in': round((self.refresh_at - datetime.datetime.utcnow()).total_seconds()),
                'token_type': 'bearer',
                'token_id': self.id}
        if access_token:
            data['access_token'] = access_token
        if refresh_token:
            data['refresh_token'] = refresh_token

        return data

    def set_refresh(self, app, refreshable=True):
        if not refreshable or 'refresh_token' not in self.client.allowed_oauth2_grant_types:
            self.refresh_at = self.expire_at
            return None

        self.refresh_at = datetime.datetime.utcnow() + datetime.timedelta(0, TOKEN_LIFETIME)

        # Expire scopes that have limited lifetimes
        alive_for = (datetime.datetime.utcnow() - self.granted_at).total_seconds()
        self.scopes = [scope for scope in self.scopes if not (scope.lifetime and scope.lifetime < alive_for)]
        lifetimes = set(filter(None, (scope.lifetime for scope in self.scopes)))
        if lifetimes:
            self.refresh_at = min(self.refresh_at,
                                  datetime.datetime.utcnow() + datetime.timedelta(seconds=min(lifetimes)))

        if self.expire_at and self.refresh_at > self.expire_at:
            self.refresh_at = self.expire_at
            refresh_token = None
        else:
            refresh_token = generate_token()
        self.refresh_token_hash = hash_token(app, refresh_token)
        return refresh_token

    def refresh(self, app, session, *, scopes=None):
        if scopes:
            self.scopes = list(set(self['scopes']) & set(scopes))
        access_token = generate_token()
        self.access_token_hash = hash_token(app, access_token)
        refresh_token = self.set_refresh(app)
        return access_token, refresh_token

    @classmethod
    def create_access_token(cls, *, app, session,
                            granted_at,
                            client, account, user_id, scopes,
                            expires=None, refreshable=True,
                            parent=None):
        if expires is True:
            expires = TOKEN_LIFETIME
        if isinstance(expires, int):
            expires = datetime.datetime.utcnow() + datetime.timedelta(0, expires)
        access_token = generate_token()
        token = cls(id=generate_token(),
                    access_token_hash=hash_token(app, access_token),
                    client=client,
                    account=account,
                    user_id=user_id,
                    scopes=list(scopes),
                    granted_at=granted_at,
                    expire_at=expires,
                    parent=parent)
        refresh_token = token.set_refresh(app, refreshable)
        session.add(token)
        return token, (access_token, refresh_token)

    def create_child_token(self, *, app, session):
        return type(self).create_access_token(app=app,
                                              session=session,
                                              client=self.client,
                                              account=self.account,
                                              scopes=self.scopes,
                                              expires=self.expire_at,
                                              parent=self)

    @classmethod
    def authenticate(cls, *, app, session, access_token, token_id=None):
        authentication_scheme = 'Bearer realm="{}"'.format(app['auth-realm'])
        access_token_hash = hash_token(app, access_token)
        token = session.query(Token).filter_by(access_token_hash=access_token_hash).first()
        if not token:
            raise cls.NotFound
        if token.remaining_uses is not None:
            remaining_uses = session.scalar(
                Token.__table__.update()
                    .where(Token.access_token_hash==access_token_hash)
                    .values({Token.remaining_uses: Token.remaining_uses - 1})
                    .returning(Token.remaining_uses))
            if remaining_uses is not None and remaining_uses < 0:
                raise cls.Overused
        if token.refresh_at and token.refresh_at <= datetime.datetime.utcnow():
            raise cls.Expired
        return token

EphemeralToken = collections.namedtuple('EphemeralToken',
                                        ('client_id', 'client',
                                         'account_id', 'account',
                                         'scopes', 'user_id'))

