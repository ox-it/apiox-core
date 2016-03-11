import asyncio
import enum
import re

from aiogrouper import Subject, Group
from sqlalchemy import Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import select
from sqlalchemy_utils.types.choice import ChoiceType

from apiox.core.db.scope import Scope
from . import Base
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


principal_administrator = Table('principal_administrator', Base.metadata,
    Column('principal_id', String(TOKEN_LENGTH), ForeignKey('principal.id'), primary_key=True),
    Column('administrator_id', String(TOKEN_LENGTH), ForeignKey('principal.id'), primary_key=True),
)

class Principal(Base):
    __tablename__ = 'principal'

    id = Column(String(TOKEN_LENGTH), primary_key=True)
    secret_hash = Column(String(TOKEN_HASH_LENGTH), nullable=True)
    name = Column(String(), unique=True, index=True)
    user_id = Column(Integer, nullable=True)
    type = Column(ChoiceType(PrincipalType))
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    redirect_uris = Column(ARRAY(String))
    allowed_oauth2_grant_types = Column(ARRAY(String))

    #account_token = relationship('Token', 'Token.account_id', backref='account')
    #client_token = relationship('Token', 'Token.client_id', backref='client')
    administrator_of = relationship('Principal', secondary=principal_administrator,
                                  primaryjoin=(id==principal_administrator.c.principal_id),
                                  secondaryjoin=(id==principal_administrator.c.administrator_id))

    administrators = relationship('Principal', secondary=principal_administrator,
                                    primaryjoin=(id==principal_administrator.c.administrator_id),
                                    secondaryjoin=(id==principal_administrator.c.principal_id))

    def is_secret_valid(self, app, secret):
        if not self.secret_hash:
            return False
        return hash_token(app, secret) == self.secret_hash

    def get_token_as_self(self, session):
        from .token import Token
        scopes = set()
        if self.is_person:
            scopes.update(session.query(Scope).filter_by(granted_to_user=True).all())

        granted_scope_ids = set()
        for scope_grant in session.query(ScopeGrant).filter_by(client_id=self.id).all():
            granted_scope_ids.update(s.id for s in scope_grant.scopes)
        if granted_scope_ids:
            scopes.update(session.query(Scope).filter(Scope.id.in_(granted_scope_ids)).all())

        from .token import EphemeralToken
        return EphemeralToken(client_id=self.id,
                              client=self,
                              account_id=self.id,
                              account=self,
                              user_id=self.user_id,
                              scopes=list(scopes))

    @asyncio.coroutine
    def get_permissible_scopes_for_user(self, app, session, user_id, *, token=None, only_implicit=True):
        if self.is_person and user_id == self.user_id:
            return set(session.query(Scope).filter_by(granted_to_user=True).all())
        results = yield from self.get_permissible_scopes_for_users(app, session, [user_id],
                                                                   only_implicit=only_implicit)
        scopes = results.popitem()[1]

        if token is not None:
            scopes.update(token.scopes)

        return scopes

    @asyncio.coroutine
    def get_permissible_scopes_for_users(self, app, session, user_ids, *, only_implicit=True):
        scope_grants = list(self.scope_grants)
        if only_implicit is False:
            scope_grants.extend(self.scope_request_grants)

        target_groups = set()
        universal_scopes = set()
        for scope_grant in scope_grants:
            if scope_grant.target_groups is None:
                universal_scopes.update(scope_grant.scopes)
            else:
                target_groups |= set(scope_grant.target_groups)

        memberships = yield from app['grouper'].get_memberships(members=[Subject(id=u) for u in user_ids],
                                                                groups=[Group(self._app['grouper'], uuid=g) for g in target_groups])
        result = {}
        for subject, in_groups in memberships.items():
            in_groups = set(g.uuid for g in in_groups)
            scopes = universal_scopes.copy()
            if self.is_person and subject.id == self.user_id:
                scopes.update(session.query(Scope).filter_by(granted_to_user=True).all())
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
    def lookup(cls, app, session, *, id=None, name=None):

        try:
            if id is not None:
                principal = session.query(cls).filter_by(id=id).first()
            elif name is not None:
                if '@' not in name:
                    name = name + '@' + app['default-realm']
                principal = session.query(cls).filter_by(name=name).one()
            else:
                raise TypeError
        except NoResultFound:
            try:
                data = app['ldap'].get_principal(name)
            except ldap.NoSuchLDAPObject:
                data = {}
            user_id = ldap.parse_person_dn(data['oakPerson'][0]) if 'oakPerson' in data else None

            principal = Principal(id=generate_token(),
                                  name=name,
                                  user_id=user_id,
                                  type=cls.determine_principal_type(app, name, user_id))
            session.add(principal)
        return principal

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

    def may_administrate(self, token):
        if not token:
            return False
        if token.account not in self.administrators:
            return False
        if not any (s.id == '/oauth2/manage-client' for s in token.scopes):
            return False
        return True

    def principal_to_json(self, app, verbose=False):
        body = {
            'id': self.id,
            'name': self.name,
            '_links': {},
        }
        if self.user_id:
            body['_links']['user'] = {'href': app.router['person:detail'].url(parts={'id': self.user_id})}
        return body

    def client_to_json(self, app, may_administrate=False):
        body = {
            'id': self.id,
            'name': self.name,
            'title': self.title,
            'description': self.description,
            '_links': {
                'self':{
                    'href': app.router['client:detail'].url(parts={'id': self.id})
                },
            },
        }
        if may_administrate:
            body.update({
                'oauth2GrantTypes': self.allowed_oauth2_grant_types,
                'redirectURIs': self.redirect_uris,
                '_links': {
                    'administrator': [a.principal_to_json(app, verbose=False) for a in self.administrators],
                    'self': {'href': app.router['client:detail'].url(parts={'id': self.id})},
                },
            })
            body['_links']['api:secret'] = {
                'href': app.router['client:secret'].url(parts={'id': self.id}),
                'title': 'Generate or remove client secret',
                'description': 'POST to generate a client secret, replacing any existing secret. DELETE to remove any '
                               'existing secret.',
            }
        return body
