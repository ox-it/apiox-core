API = 'api'
CLIENT = 'client'

_scope_schema = {
    'properties': {
        'id': {'type': 'string', 'pattern': '^[a-z/\-0-9]+$'},
        'title': {'type': 'string'},
        'description': {'type': 'string'},
        'grantedToUser': {'type': 'boolean', 'default': False},
        'personal': {'type': 'boolean', 'default': False},
        'lifetime': {'type': 'number'},
        'advertise': {'type': 'boolean', 'default': True},
        'aliases': {
            'type': 'array',
            'items': {'type': 'string', 'pattern': '^[!#-[]-~]+$'},
            'minItems': 1,
            'uniqueItems': True,
        },
    },
    'required': ['id', 'name'],
}

_api_schema = {
    'properties': {
        'id': {'type': 'string', 'pattern': '^[a-z][a-z0-9\-]*$'},
        'title': {'type': 'string'},
        'description': {'type': 'string'},
        'raml': {'type': 'string', 'format': 'url'},
        'base': {'type': 'string'},
        'localImplementation': {'type': 'string'},
        'scopes': {
            'type': 'array',
            'items': _scope_schema,
        },
        'requireScope': {
            'type': 'array',
            'items': {'type': 'string'},
            'minItems': 1,
            'uniqueItems': True,
        },
        'requireUser': {'type': 'boolean', 'default': False},
        'requireAuth': {'type': 'boolean', 'default': False},
        'requireGroup': {'type': 'string'},
        'requireRole': {
            'type': 'array',
            'items': {
                'type': 'string',
                'pattern': '^[a-z]+$',
            },
            'uniqueItems': True,
        },
        'available':  {'type': 'boolean', 'default': True},
        'paths': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'allowMethods': {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                            'pattern': '^[A-Z]+$',
                        },
                        'uniqueItems': True
                    },
                    'sourcePath': {'type': 'string'},
                    'targetPath': {'type': 'string'},
                    'requireScope': {'oneOf': [{
                        'type': 'array',
                        'items': {'type': 'string'},
                        'minItems': 1,
                        'uniqueItems': True,
                    }, {
                        'type': 'null',
                    }]},
                    'requireUser': {'type': 'boolean', 'default': False},
                    'requireAuth': {'type': 'boolean', 'default': False},
                    'requireRole': {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                            'pattern': '^[a-z]+$',
                        },
                        'uniqueItems': True,
                    },
                    'available':  {'type': 'boolean', 'default': True},
                },
                'required': ['sourcePath', 'targetPath'],
            },
        },
    },
    'required': ['id', 'name'],
}

_client_schema = {
    'properties': {
        'id': {'type': 'string'},
        'title': {'type': 'string'},
        'description': {'type': 'string'},
    }
}

schemas = {
    API: _api_schema,
    CLIENT: _client_schema,
}
