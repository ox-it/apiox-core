from .basic import basic_auth_middleware
from .negotiate import negotiate_auth_middleware, add_negotiate_token
from .oauth2 import oauth2_middleware
from .remote_user import remote_user_middleware