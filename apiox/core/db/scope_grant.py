from sqlalchemy import Table, Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.dialects.postgres import ARRAY

from ..token import TOKEN_LENGTH

from . import metadata, Instance

scope_grant = Table('apiox_scope_grant', metadata,
    Column('id', Integer, primary_key=True),
    Column('client_id', String(TOKEN_LENGTH), ForeignKey('principal.id')),
    Column('scopes', ARRAY(String(255))),
    Column('target_groups', ARRAY(String(32))),

    Column('granted_at', DateTime(True)),
    Column('review_at', DateTime(True)),
    Column('expire_at', DateTime(True), nullable=True),

    Column('justification', String, default=''),
    Column('notes', String, default=''),
)

class ScopeGrant(Instance):
    table = scope_grant