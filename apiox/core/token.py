import random

TOKEN_LENGTH = 32
TOKEN_LIFETIME = 600
TOKEN_ALPHABET = 'abcdefghijklmnopqrstuvwxyz' \
                 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                 '0123456789'

def generate_token():
    return ''.join(random.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))