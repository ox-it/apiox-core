from collections import namedtuple, OrderedDict
import datetime

SCOPE_GRANT_REVIEW = datetime.timedelta(days=365)
SCOPE_GRANT_EXPIRE = datetime.timedelta(days=395)

fields = ('name',
          'title',
          'description',
          'available_to_user',
          'available_to_client',
          'requestable_by_all_clients',
          'require_principal_type',
          'personal',
          'lifetime',
          'end_user_policy')

class Scopes(OrderedDict):
    def add(self, scope=None, **kwargs):
        if scope is None:
            scope = Scope(**kwargs)
        self[scope.name] = scope

class Scope(namedtuple('ScopeBase', fields)):
    def __new__(cls, *,
                name, title, description,
                available_to_user=False,
                available_to_client=False,
                requestable_by_all_clients=False,
                require_principal_type=None,
                lifetime=None,
                end_user_policy=None):
        _locals = locals()
        return super().__new__(cls, **{n: _locals[n] for n in fields})
