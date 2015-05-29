DEBUG = True

SECRET_KEY = 'secret'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'apiox',
    },
}

INSTALLED_APPS = (
    'oxapiauth',
)