import random
import hashlib

TOKEN_LENGTH = 32
TOKEN_LIFETIME = 600
TOKEN_ALPHABET = 'abcdefghijklmnopqrstuvwxyz' \
                 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                 '0123456789'
TOKEN_HASH = hashlib.sha256
TOKEN_HASH_LENGTH = len(TOKEN_HASH(b'').hexdigest())

def generate_token():
    return ''.join(random.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))

def hash_token(app, token):
    return TOKEN_HASH(token.encode() + app['token-salt']).hexdigest()