from sqlalchemy import Table, Column, Integer, ForeignKey, String, DateTime, Boolean
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.orm import relationship

from ..token import TOKEN_LENGTH

from . import Base

__all__ = ['ScopeGrant', 'ScopeRequestGrant']

# A scope grant grants a scope to a client acting as itself
# A scope request grant allows a client to request scopes on behalf of a user

scope_grant_scope = Table('scope_grant_scope', Base.metadata,
    Column('scope_id', String, ForeignKey('scope.id'), primary_key=True),
    Column('scope_grant_id', Integer, ForeignKey('scope_grant.id'), primary_key=True),
)

scope_request_grant_scope = Table('scope_request_grant_scope', Base.metadata,
    Column('scope_id', String, ForeignKey('scope.id'), primary_key=True),
    Column('scope_request_grant_id', Integer, ForeignKey('scope_request_grant.id'), primary_key=True),
)


class ScopeGrant(Base):
    __tablename__ = 'scope_grant'

    id = Column(Integer, primary_key=True)
    client_id = Column(String(TOKEN_LENGTH), ForeignKey('principal.id'))
    target_groups = Column(ARRAY(String(32)))

    client = relationship('Principal', backref='scope_grants')
    scopes = relationship('Scope', secondary=scope_grant_scope, backref='scope_grants')

    granted_at = Column(DateTime)
    review_at = Column(DateTime)
    expire_at = Column(DateTime)

    justification = Column(String, default='')
    notes = Column(String, default='')

class ScopeRequestGrant(Base):
    __tablename__ = 'scope_request_grant'

    id = Column(Integer, primary_key=True)
    client_id = Column(String(TOKEN_LENGTH), ForeignKey('principal.id'))
    target_groups = Column(ARRAY(String(32)))

    client = relationship('Principal', backref='scope_request_grants')
    scopes = relationship('Scope', secondary=scope_request_grant_scope, backref='scope_request_grants')

    granted_at = Column(DateTime)
    review_at = Column(DateTime)
    expire_at = Column(DateTime)

    justification = Column(String, default='')
    notes = Column(String, default='')
