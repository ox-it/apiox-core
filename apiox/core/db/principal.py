import asyncio
import enum
import re

from aiogrouper import Subject, Group
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy.sql import select
from sqlalchemy_utils.types.choice import ChoiceType

from . import metadata, Instance
from .. import ldap
from ..token import TOKEN_LENGTH, TOKEN_HASH_LENGTH, hash_token, generate_token
from sqlalchemy.dialects.postgresql.base import ARRAY

from .scope_grant import ScopeGrant

class PrincipalType(enum.Enum):
    user = 'user'
    project = 'project'
    society = 'society'
    service = 'service'
    itss = 'ITSS'
    root = 'root'
    admin = 'admin'

principal = Table('apiox_principal', metadata,
    Column('id', String(TOKEN_LENGTH), primary_key=True),
    Column('secret_hash', String(TOKEN_HASH_LENGTH), nullable=True),
    Column('name', String(), unique=True, index=True),
    Column('user_id', Integer, nullable=True),
    Column('type', ChoiceType(PrincipalType)),
    Column('administrators', ARRAY(Integer)),
    Column('title', String, nullable=True),
    Column('description', String, nullable=True),
    Column('redirect_uris', ARRAY(String)),
    Column('allowed_oauth2_grants', ARRAY(String)),
)

class Principal(Instance):
    table = principal

    def is_secret_valid(self, app, secret):
        if not self['secret_hash']:
            return False
        return hash_token(app, secret) == self['secret_hash']

    def get_token_as_self(self, app):
        from .token import Token
        scopes = set()
        if self.is_oauth2_client:
            scopes.update(s.name for s in app['scopes'].values() if s.available_to_client)
        if self.is_person:
            scopes.update(s.name for s in app['scopes'].values() if s.available_to_user)
        for scope_grant in self.scopegrant_set.all():
            scopes.update(s for s in scope_grant.scopes if not app['scopes'][s].personal)
        return Token(client=self,
                     account=self,
                     user_id=self['user_id'],
                     scopes=list(scopes))

    @asyncio.coroutine
    def get_permissible_scopes_for_user(self, app, user_id):
        if self.is_person and user_id == self['user_id']:
            return set(s.name for s in app['scopes'].values() if s.available_to_user)
        results = yield from self.get_permissible_scopes_for_users(app, [user_id])
        return results.popitem()[1]

    @asyncio.coroutine
    def get_permissible_scopes_for_users(self, app, user_ids):
        scope_grants = yield from ScopeGrant.all(app, client_id=self['id'])
        target_groups = set()
        for scope_grant in scope_grants:
            target_groups |= set(scope_grant['target_groups'])

        memberships = yield from app['grouper'].get_memberships(members=[Subject(id=u) for u in user_ids],
                                                                groups=[Group(uuid=g) for g in target_groups])
        result = {}
        for subject, in_groups in memberships.items():
            in_groups = set(g.uuid for g in in_groups)
            scopes = set()
            if self.is_person and subject.id == self.user:
                scopes.update(s.name for s in app['scopes'].values() if s.available_to_user)
            for scope_grant in scope_grants:
                if in_groups & set(scope_grant['target_groups']):
                    scopes |= set(scope_grant['scopes'])
            result[int(subject.id)] = scopes
        return result

    @property
    def is_person(self):
        return self.type in {'user', 'itss', 'root', 'admin'}

    @classmethod
    def lookup(cls, app, name):
        if '@' not in name:
            name = name + '@' + app['default-realm']
        try:
            data = app['ldap'].get_principal(name)
        except ldap.NoSuchLDAPObject:
            data = {}
        user_id = ldap.parse_person_dn(data['oakPerson'][0]) if 'oakPerson' in data else None
        
        principal = yield from cls.get(app, name=name)
        if principal:
            principal = Principal(principal)
        else:
            principal = Principal(id=generate_token(),
                                  name=name,
                                  user_id=user_id,
                                  type=principal.determine_principal_type(app, name, user_id))
            yield from principal.insert()
        return principal

    @classmethod
    def determine_principal_type(cls, app, name, user_id):
        name = name.split('@')[0].split('/')
        first, last = name[0], name[1] if len(name) > 1 else None
        user = app['ldap'].get_person(user_id) if user_id else None
        if last and '.' in last:
            return 'service'
        elif not user:
            return 'society'
        elif first not in (ldap.parse_principal_dn(user['oakPrincipal'][0]),
                           user['oakOxfordSSOUsername'][0]) \
             and not re.match('^[a-z]{4}\d{4}$', first):
            return 'project'
        elif not last:
            return 'user'
        else:
            return last