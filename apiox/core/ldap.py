import functools
import re
import threading

import ldap
import ldap.sasl

PRINCIPAL_NAME_RE = re.compile(r'^[a-z\d\-]+(?:/[a-z\d\-.]+)?$')
PERSON_DN_RE = re.compile(r'^oakPrimaryPersonID=(\d+),ou=people,dc=oak,dc=ox,dc=ac,dc=uk$')
PRINCIPAL_DN_RE = re.compile(r'^krbPrincipalName=([\da-z_/]+)@OX.AC.UK,cn=OX.AC.UK,cn=KerberosRealms,dc=oak,dc=ox,dc=ac,dc=uk$')

_local = threading.local()

class NoSuchLDAPObject(Exception):
    pass

def _get_ldap_connection(app):
    auth = ldap.sasl.gssapi("")
    conn = ldap.initialize(app['ldap-url'])
    conn.start_tls_s()
    conn.sasl_interactive_bind_s("", auth)
    return conn

def _with_ldap_connection(func):
    @functools.wraps(func)
    def f(app, *args, **kwargs):
        if not hasattr(_local, 'conn'):
            _local.conn = _get_ldap_connection(app)
        try:
            return func(_local.conn, *args, **kwargs)
        except ldap.SERVER_DOWN: # Try again, once
            _local.conn = _get_ldap_connection()
            return func(_local.conn, *args, **kwargs)
    return f

def _decode_result(result):
    for k in result:
        if isinstance(result[k], bytes):
            result[k] = result[k].decode()
        elif isinstance(result[k], list):
            result[k] = [v.decode() for v in result[k]]
    return result

@_with_ldap_connection
def get_person(conn, person_id):
    try:
        results = conn.search_s("oakPrimaryPersonID={:d},ou=people,dc=oak,dc=ox,dc=ac,dc=uk".format(person_id),
                                ldap.SCOPE_BASE)
        return _decode_result(results[0][1])
    except (ldap.NO_SUCH_OBJECT, IndexError):
        raise NoSuchLDAPObject

@_with_ldap_connection
def get_principal(conn, name):
    if not PRINCIPAL_NAME_RE.match(name):
        raise ValueError("Not a valid principal name: {!r}".format(name))
    try:
        results = conn.search_s("krbPrincipalName={:s}@OX.AC.UK,cn=OX.AC.UK,cn=KerberosRealms,dc=oak,dc=ox,dc=ac,dc=uk".format(name),
                                ldap.SCOPE_BASE)
        return _decode_result(results[0][1])
    except (ldap.NO_SUCH_OBJECT, IndexError):
        raise NoSuchLDAPObject

def parse_person_dn(dn):
    return int(PERSON_DN_RE.match(dn).group(1))

def parse_principal_dn(dn):
    return PRINCIPAL_DN_RE.match(dn).group(1)