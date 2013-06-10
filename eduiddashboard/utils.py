from hashlib import sha256


def verify_auth_token(shared_key, public_word, token, generator=sha256):
    return token == generator("{0}{1}".format(shared_key, public_word)).hexdigest()
