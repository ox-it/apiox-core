import datetime
import functools
import re

from django.db import models
from django.contrib.postgres.fields import ArrayField

from .ldap import get_principal, get_person, NoSuchLDAPObject, parse_person_dn, parse_principal_dn
from .token import generate_token, TOKEN_LENGTH, TOKEN_LIFETIME

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
    allowed_scopes = ArrayField(models.CharField(max_length=128), default=[])
    redirect_uris = ArrayField(models.URLField(), default=[])

    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=128)

    allow_password_authentication = models.BooleanField(default=False)
    is_oauth2_client = models.BooleanField(default=False)

    class Meta:
        db_table = 'apiox_principal'

    def is_password_valid(self, password):
        return self.allow_password_authentication
    
    def get_token_as_self(self, app):
        scopes = set()
        if self.is_oauth2_client:
            scopes.update(s.name for s in app['scopes'].values() if s.available_to_client)
        if self.type in {'user', 'itss', 'root', 'admin'}:
            scopes.update(s.name for s in app['scopes'].values() if s.available_to_user)
        return Token(client=self,
                     account=self,
                     user=self.user,
                     scopes=list(scopes))

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
    access_token = models.CharField(max_length=TOKEN_LENGTH)
    refresh_token = models.CharField(max_length=TOKEN_LENGTH, blank=True)

    client = models.ForeignKey(Principal, related_name='client_tokens')
    account = models.ForeignKey(Principal, related_name='account_tokens')
    user = UserField(null=True, blank=True)

    scopes = ArrayField(models.CharField(max_length=256), default=[])

    refresh_at = models.DateTimeField()
    expire_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'apiox_token'

    def as_json(self):
        data = {'scopes': sorted(self.scopes),
                'expires_in': round((self.refresh_at - datetime.datetime.utcnow()).total_seconds()),
                'token_type': 'bearer'}
        if self.access_token:
            data['access_token'] = self.access_token
        if self.refresh_token:
            data['refresh_token'] = self.refresh_token
        
        return data

    def set_refresh(self):
        self.refresh_at = datetime.datetime.utcnow() + datetime.timedelta(0, TOKEN_LIFETIME)
        if self.expire_at and self.refresh_at > self.expire_at:
            self.refresh_at = self.expire_at
            self.refresh_token = None
        else:
            self.refresh_token = generate_token()

    def refresh(self, scopes=None):
        if scopes:
            self.scopes = set(self.scopes) & set(scopes)
        self.access_token = generate_token()
        self.set_refresh()
        self.save()

    @classmethod
    def create_access_token(cls, client, account, user, scopes, expires=None, refreshable=True):
        if expires is True:
            expires = TOKEN_LIFETIME
        if isinstance(expires, int):
            expires = datetime.datetime.utcnow() + datetime.timedelta(0, expires)
        token = cls(access_token=generate_token(),
                    client=client,
                    account=account,
                    user=user,
                    scopes=list(scopes),
                    expire_at=expires)
        token.set_refresh()
        return token

class AuthorizationCode(models.Model):
    code = models.CharField(max_length=TOKEN_LENGTH, blank=True)
    
    client = models.ForeignKey(Principal, related_name='client_codes')
    account = models.ForeignKey(Principal, related_name='account_codes')
    user = UserField()
    scopes = ArrayField(models.CharField(max_length=256), default=[])
    redirect_uri = models.URLField(null=True, blank=True)

    expire_at = models.DateTimeField(default=lambda:datetime.datetime.utcnow() + datetime.timedelta(0, 600))
    token_expire_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'apiox_authorization_code'

    def convert_to_access_token(self):
        self.delete()
        return Token.create_access_token(client=self.client,
                                         account=self.account,
                                         user=self.user,
                                         scopes=self.scopes,
                                         expires=self.token_expire_at)

class ScopeGrant(models.Model):
    token = models.ForeignKey(Token)
    scope = models.CharField(max_length=256)
    expire_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'apiox_scope_grant'

