import hashlib


def hash_string(string: str):
    return str(hashlib.sha1(string.encode("utf-8")).hexdigest())

print(hash_string('ezt hasheld'))