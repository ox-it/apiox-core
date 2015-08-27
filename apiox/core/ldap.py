import functools
import re

import ldap3

PRINCIPAL_NAME_RE = re.compile(r'^[A-Za-z0-9\-]+(?:/[A-Za-z0-9\-.]+)?@[A-Z.]+$')
PERSON_DN_RE = re.compile(r'^oakPrimaryPersonID=(\d+),ou=people,dc=oak,dc=ox,dc=ac,dc=uk$')
PRINCIPAL_DN_RE = re.compile(r'^krbPrincipalName=([0-9a-zA-Z_/]+)@OX.AC.UK,cn=OX.AC.UK,cn=KerberosRealms,dc=oak,dc=ox,dc=ac,dc=uk$')

class NoSuchLDAPObject(Exception):
    pass

def _with_ldap_connection(func):
    @functools.wraps(func)
    def f(self, *args, **kwargs):
        if not hasattr(self, '_conn'):
            self._conn = self._get_ldap_connection()
        try:
            return func(self._conn, *args, **kwargs)
        except Exception: # Try again, once
            self._conn = self._get_ldap_connection()
            return func(self._conn, *args, **kwargs)
    return f

class LDAP(object):
    def __init__(self, url, user):
        self.url, self.user = url, user

    def _get_ldap_connection(self):
        conn = ldap3.Connection(self.url,
                                authentication=ldap3.SASL,
                                sasl_mechanism='GSSAPI',
                                sasl_credentials=(True,),
                                user=self.user)
        conn.bind()
        return conn

    @_with_ldap_connection
    def get_person(self, conn, person_id):
        try:
            conn.search("oakPrimaryPersonID={:d},ou=people,dc=oak,dc=ox,dc=ac,dc=uk".format(person_id),
                        search_filter='(objectClass=*)',
                        search_scope=ldap3.BASE,
                        attributes=ldap3.ALL_ATTRIBUTES)
            return conn.response[0]['attributes']
        except (IndexError):
            raise NoSuchLDAPObject

    @_with_ldap_connection
    def get_principal(self, conn, name):
        if not PRINCIPAL_NAME_RE.match(name):
            raise ValueError("Not a valid principal name: {!r}".format(name))
        try:
            local, realm = name.split('@')
            conn.search("krbPrincipalName={local}@{realm},cn={realm:s},cn=KerberosRealms,dc=oak,dc=ox,dc=ac,dc=uk".format(local=local,
                                                                                                                              realm=realm),
                        search_filter='(objectClass=*)',
                        search_scope=ldap3.BASE,
                        attributes=ldap3.ALL_ATTRIBUTES)
            #import pdb;pdb.set_trace()
            return conn.response[0]['attributes']
        except (IndexError):
            raise NoSuchLDAPObject

    @_with_ldap_connection
    def search(self, conn, **kwargs):
        conn.search(**kwargs)
        return conn.response

def parse_person_dn(dn):
    return int(PERSON_DN_RE.match(dn).group(1))

def parse_principal_dn(dn):
    return PRINCIPAL_DN_RE.match(dn).group(1)

_escape_characters = frozenset('*\\()\0')
def escape(s):
    return ''.join(r'\{:X}'.format(c) if c in _escape_characters else c
                   for c in s)
