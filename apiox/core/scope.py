from collections import namedtuple

fields = ('name',
          'description',
          'available_to_user',
          'available_to_client',
          'require_principal_type')

class Scope(namedtuple('ScopeBase', fields)):
    def __new__(cls, name, description,
                available_to_user=False,
                available_to_client=False,
                require_principal_type=None):
        _locals = locals()
        return super().__new__(cls, **{n: _locals[n] for n in fields})
