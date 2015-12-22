import asyncio
from sqlalchemy import Table, Column, String, Integer, DateTime, ForeignKey, Sequence
from sqlalchemy.orm import relationship

from . import Base
from apiox.core.token import TOKEN_HASH_LENGTH, TOKEN_LENGTH
from sqlalchemy.dialects.postgresql import ARRAY

from .token import Token

__all__ = ['AuthorizationCode']

authorization_code_scope = Table('authorization_code_scope', Base.metadata,
    Column('authorization_code_id', Integer, ForeignKey('authorization_code.id'), primary_key=True),
    Column('scope_id', String, ForeignKey('scope.id'), primary_key=True),
)


class AuthorizationCode(Base):
    __tablename__ = 'authorization_code'

    id = Column(Integer, Sequence('authorization_code_id_seq'), primary_key=True)

    code_hash = Column(String(TOKEN_HASH_LENGTH), index=True)

    client_id = Column(String(TOKEN_LENGTH), ForeignKey('principal.id'))
    account_id = Column(String(TOKEN_LENGTH), ForeignKey('principal.id'))
    user_id = Column(Integer)
    redirect_uri = Column(String)

    scopes = relationship('Scope', secondary=authorization_code_scope, backref='authorization_codes')

    client = relationship('Principal', foreign_keys=[client_id])
    account = relationship('Principal', foreign_keys=[account_id])

    granted_at = Column(DateTime())
    expire_at = Column(DateTime())
    token_expire_at = Column(DateTime(), nullable=True)

    def convert_to_access_token(self, app, session):
        token = Token.create_access_token(app=app,
                                          session=session,
                                          client=self.client,
                                          account=self.account,
                                          user_id=self.user_id,
                                          scopes=self.scopes,
                                          granted_at=self.granted_at,
                                          expires=self.token_expire_at)
        session.delete(self)
        return token