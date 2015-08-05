import asyncio
import datetime
import functools
import re

from django.db import models
from django.contrib.postgres.fields import ArrayField

from .ldap import get_principal, get_person, NoSuchLDAPObject, parse_person_dn, parse_principal_dn
from .scope import SCOPE_GRANT_REVIEW, SCOPE_GRANT_EXPIRE
from .token import generate_token, hash_token, TOKEN_LENGTH, TOKEN_HASH_LENGTH, TOKEN_LIFETIME

from aiogrouper import Group, SubjectLookup

PRINCIPAL_TYPE_CHOICES = (
    ('user', 'User'),
    ('project', 'Project'),
    ('society', 'Society'),
    ('service', 'Service'),
    ('itss', 'ITSS'),
    ('root', 'Root'),
    ('admin', 'Admin'),
)

PrincipalField = functools.partial(models.CharField, max_length=256)
UserField = functools.partial(models.IntegerField)


class Principal(models.Model):
    name = PrincipalField(primary_key=True)
    user = UserField(null=True, blank=True)
    type = models.CharField(max_length=32, choices=PRINCIPAL_TYPE_CHOICES)
    administrators = ArrayField(UserField(), default=[])
    title = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)
    redirect_uris = ArrayField(models.URLField(), default=[])

    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=128)

    allow_password_authentication = models.BooleanField(default=False)
    is_oauth2_client = models.BooleanField(default=False)

    class Meta:
        db_table = 'apiox_principal'

    def is_password_valid(self, password):
        if not self.allow_password_authentication:
            return False
        return True

    def get_token_as_self(self, app):
        scopes = set()
        if self.is_oauth2_client:
            scopes.update(s.name for s in app['scopes'].values() if s.available_to_client)
        if self.is_person:
            scopes.update(s.name for s in app['scopes'].values() if s.available_to_user)
        for scope_grant in self.scopegrant_set.all():
            scopes.update(s for s in scope_grant.scopes if not app['scopes'][s].personal)
        return Token(client=self,
                     account=self,
                     user=self.user,
                     scopes=list(scopes))

    @asyncio.coroutine
    def get_permissible_scopes_for_user(self, app, user):
        if self.is_person and user == self.user:
            return set(s.name for s in app['scopes'].values() if s.available_to_user)
        scope_grants = self.scopegrant_set.all()
        target_groups = set()
        for scope_grant in scope_grants:
            target_groups |= set(scope_grant.target_groups)
        in_groups = yield from app['grouper'].get_subject_memberships(SubjectLookup(identifier=user),
                                                                      [Group(uuid=g) for g in target_groups])
        in_groups = set(g.uuid for g in in_groups)
        scopes = set()
        for scope_grant in scope_grants:
            if in_groups & set(scope_grant.target_groups):
                scopes |= set(scope_grant.scopes)
        return scopes

    @property
    def is_person(self):
        return self.type in {'user', 'itss', 'root', 'admin'}

    @classmethod
    def lookup(cls, app, name):
        try:
            data = get_principal(app, name)
        except NoSuchLDAPObject as e:
            raise Principal.DoesNotExist from e
        user = parse_person_dn(data['oakPerson'][0]) if 'oakPerson' in data else None
        try:
            principal, created = Principal.objects.get(name=name), False
        except Principal.DoesNotExist:
            principal, created = Principal(name=name), True
        if principal.user != user or created:
            principal.user = user
            principal.type = principal.determine_principal_type(app)
            principal.save()
        return principal

    def determine_principal_type(self, app):
        name = self.name.split('/')
        first, last = name[0], name[1] if len(name) > 1 else None
        user = get_person(app, self.user) if self.user else None
        if last and '.' in last:
            return 'service'
        elif not user:
            return 'society'
        elif first not in (parse_principal_dn(user['oakPrincipal'][0]),
                           user['oakOxfordSSOUsername'][0]) \
             and not re.match('^[a-z]{4}\d{4}$', first):
            return 'project'
        elif not last:
            return 'user'
        else:
            return last


class Token(models.Model):
    id = models.CharField(max_length=TOKEN_LENGTH, primary_key=True, default=generate_token)
    access_token_hash = models.CharField(max_length=TOKEN_HASH_LENGTH)
    refresh_token_hash = models.CharField(max_length=TOKEN_HASH_LENGTH, blank=True)

    client = models.ForeignKey(Principal, related_name='client_tokens')
    account = models.ForeignKey(Principal, related_name='account_tokens')
    user = UserField(null=True, blank=True)

    scopes = ArrayField(models.CharField(max_length=256), default=[])

    granted_at = models.DateTimeField()
    refresh_at = models.DateTimeField()
    expire_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'apiox_token'

    def as_json(self, *, access_token=None, refresh_token=None):
        data = {'scopes': sorted(self.scopes),
                'expires_in': round((self.refresh_at - datetime.datetime.utcnow()).total_seconds()),
                'token_type': 'bearer',
                'token_id': self.id}
        if access_token:
            data['access_token'] = access_token
        if refresh_token:
            data['refresh_token'] = refresh_token
        
        return data

    def set_refresh(self, app):
        self.refresh_at = datetime.datetime.utcnow() + datetime.timedelta(0, TOKEN_LIFETIME)

        # Expire scopes that have limited lifetimes
        alive_for = (datetime.datetime.utcnow() - self.granted_at).total_seconds()
        scopes = [app['scopes'][n] for n in self.scopes]
        scopes = [scope for scope in scopes if not (scope.lifetime and scope.lifetime < alive_for)]
        lifetimes = list(filter(None, (scope.lifetime for scope in scopes)))
        if lifetimes:
            self.refresh_at = min(self.refresh_at,
                                  datetime.datetime.utcnow() + datetime.timedelta(seconds=min(lifetimes)))
        self.scopes = [scope.name for scope in scopes]

        if self.expire_at and self.refresh_at > self.expire_at:
            self.refresh_at = self.expire_at
            refresh_token = None
        else:
            refresh_token = generate_token()
        self.refresh_token_hash = hash_token(app, refresh_token)
        return refresh_token

    def refresh(self, *, app, scopes=None):
        if scopes:
            self.scopes = list(set(self.scopes) & set(scopes))
        access_token = generate_token()
        self.access_token_hash = hash_token(app, access_token)
        refresh_token = self.set_refresh(app)
        self.save()
        return access_token, refresh_token

    @classmethod
    def create_access_token(cls, *, app, granted_at, client, account, user, scopes, expires=None, refreshable=True):
        if expires is True:
            expires = TOKEN_LIFETIME
        if isinstance(expires, int):
            expires = datetime.datetime.utcnow() + datetime.timedelta(0, expires)
        access_token = generate_token()
        token = cls(access_token_hash=hash_token(app, access_token),
                    client=client,
                    account=account,
                    user=user,
                    scopes=list(scopes),
                    granted_at=granted_at,
                    expire_at=expires)
        refresh_token = token.set_refresh(app)
        token.save()
        return token, (access_token, refresh_token)

class AuthorizationCode(models.Model):
    code_hash = models.CharField(max_length=TOKEN_HASH_LENGTH, blank=True)
    
    client = models.ForeignKey(Principal, related_name='client_codes')
    account = models.ForeignKey(Principal, related_name='account_codes')
    user = UserField()
    scopes = ArrayField(models.CharField(max_length=256), default=[])
    redirect_uri = models.URLField(null=True, blank=True)

    granted_at = models.DateTimeField(default=lambda:datetime.datetime.utcnow())
    expire_at = models.DateTimeField(default=lambda:datetime.datetime.utcnow() + datetime.timedelta(0, 600))
    token_expire_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'apiox_authorization_code'

    def convert_to_access_token(self, app):
        self.delete()
        return Token.create_access_token(app=app,
                                         client=self.client,
                                         account=self.account,
                                         user=self.user,
                                         scopes=self.scopes,
                                         granted_at=self.granted_at,
                                         expires=self.token_expire_at)

class ScopeGrant(models.Model):
    principal = models.ForeignKey(Principal)
    scopes = ArrayField(models.CharField(max_length=256), default=[])
    target_groups = ArrayField(models.CharField(max_length=32, blank=True))
    implicit = models.BooleanField(default=None,
                                   help_text="If True, a client doesn't need to ask the user. "
                                             "If False, they need to perform an OAuth2 authorization before they can be granted a token with any of these scopes.")
    granted_at = models.DateTimeField(default=lambda:datetime.datetime.utcnow())
    review_at = models.DateTimeField(default=lambda:datetime.datetime.utcnow() + SCOPE_GRANT_REVIEW)
    expire_at = models.DateTimeField(default=lambda:datetime.datetime.utcnow() + SCOPE_GRANT_EXPIRE)
    justification = models.TextField()
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'apiox_scope_grant'

class ScopeGrantRequest(models.Model):
    principal = models.ForeignKey(Principal)
    scopes = ArrayField(models.CharField(max_length=256), default=[])
    target_group = models.CharField(max_length=2048)
    implicit = models.BooleanField(default=None,
                                   help_text="If True, a client doesn't need to ask the user. "
                                             "If False, they need to perform an OAuth2 authorization before they can be granted a token with any of these scopes.")
    justification = models.TextField()
    