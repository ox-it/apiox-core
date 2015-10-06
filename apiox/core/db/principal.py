import asyncio
import enum
import re

from aiogrouper import Subject, Group
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy.sql import select
from sqlalchemy_utils.types.choice import ChoiceType

from . import metadata, Model
from .. import ldap
from ..token import TOKEN_LENGTH, TOKEN_HASH_LENGTH, hash_token, generate_token
from sqlalchemy.dialects.postgresql.base import ARRAY

from .scope_grant import ScopeGrant


class PrincipalType(enum.Enum):
    user = 'user'
    project = 'project'
    society = 'society'
    service = 'service'
    itss = 'itss'
    root = 'root'
    admin = 'admin'

PrincipalType.user.label = 'user'
PrincipalType.project.label = 'project account'
PrincipalType.society.label = 'club or society'
PrincipalType.service.label = 'service principal'
PrincipalType.itss.label = 'ITSS'
PrincipalType.root.label = 'root user'
PrincipalType.admin.label = 'admin user'

person_principal_types = {
    PrincipalType.user,
    PrincipalType.itss,
    PrincipalType.root,
    PrincipalType.admin,
}

principal = Table('principal', metadata,
    Column('id', String(TOKEN_LENGTH), primary_key=True),
    Column('secret_hash', String(TOKEN_HASH_LENGTH), nullable=True),
    Column('name', String(), unique=True, index=True),
    Column('user_id', Integer, nullable=True),
    Column('type', ChoiceType(PrincipalType)),
    Column('administrators', ARRAY(Integer)),
    Column('title', String, nullable=True),
    Column('description', String, nullable=True),
    Column('redirect_uris', ARRAY(String)),
    Column('allowed_oauth2_grant_types', ARRAY(String)),
)

class Principal(Model):
    table = principal

    def is_secret_valid(self, secret):
        if not self['secret_hash']:
            return False
        return hash_token(self._app, secret) == self['secret_hash']

    @asyncio.coroutine
    def get_token_as_self(self):
        from .token import Token
        scopes = set()
        if self.is_person:
            scopes.update(s.name for s in self._app['scopes'].values() if s.available_to_user)
        for scope_grant in (yield from ScopeGrant.all(self._app, client_id=self['id'])):
            scopes.update(s for s in scope_grant.scopes if not self._app['scopes'][s].personal)
        return Token(self._app,
                     client_id=self.id,
                     account_id=self.id,
                     user_id=self['user_id'],
                     scopes=list(scopes))

    @asyncio.coroutine
    def get_permissible_scopes_for_user(self, user_id, *, only_implicit=True):
        if self.is_person and user_id == self['user_id']:
            return set(s.name for s in self._app['scopes'].values() if s.available_to_user)
        results = yield from self.get_permissible_scopes_for_users([user_id],
                                                                   only_implicit=only_implicit)
        return results.popitem()[1]

    @asyncio.coroutine
    def get_permissible_scopes_for_users(self, user_ids, *, only_implicit=True):
        scope_grants = yield from ScopeGrant.all(self._app, client_id=self['id'],
                                                 **({'implicit': True} if only_implicit else {}))
        target_groups = set()
        universal_scopes = set()
        for scope_grant in scope_grants:
            if scope_grant.target_groups is None:
                universal_scopes.update(scope_grant.scopes)
            else:
                target_groups |= set(scope_grant.target_groups)

        memberships = yield from self._app['grouper'].get_memberships(members=[Subject(id=u) for u in user_ids],
                                                                      groups=[Group(self._app['grouper'], uuid=g) for g in target_groups])
        result = {}
        for subject, in_groups in memberships.items():
            in_groups = set(g.uuid for g in in_groups)
            scopes = universal_scopes.copy()
            if self.is_person and subject.id == self.user_id:
                scopes.update(s.name for s in self._app['scopes'].values() if s.available_to_user)
            for scope_grant in scope_grants:
                if scope_grant.target_groups is not None and \
                   in_groups & set(scope_grant.target_groups):
                    scopes |= set(scope_grant.scopes)
            result[int(subject.id)] = scopes
        return result

    @property
    def is_person(self):
        return self.type in person_principal_types

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
        if not principal:
            principal = Principal(app,
                                  id=generate_token(),
                                  name=name,
                                  user_id=user_id,
                                  type=cls.determine_principal_type(app, name, user_id))
            yield from principal.insert()
        return principal

    @property
    def type(self):
        value = self['type']
        if not isinstance(value, PrincipalType):
            value = PrincipalType[value]
        return value

    @classmethod
    def determine_principal_type(cls, app, name, user_id):
        name = name.split('@')[0].split('/')
        first, last = name[0], name[1] if len(name) > 1 else None
        user = app['ldap'].get_person(user_id) if user_id else None
        if last and '.' in last:
            return PrincipalType.service
        elif not user:
            return PrincipalType.society
        elif first not in (ldap.parse_principal_dn(user['oakPrincipal'][0]),
                           user['oakOxfordSSOUsername'][0]) \
             and not re.match('^[a-z]{4}\d{4}$', first):
            return PrincipalType.project
        elif not last:
            return PrincipalType.user
        else:
            return PrincipalType[last]
