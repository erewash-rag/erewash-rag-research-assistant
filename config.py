import os


def get_property(key):
    return os.environ.get(key) or _get_local_property(key)


def _get_local_property(key):
    try:
        with open("properties.txt") as fp:
            for line in fp:
                k, _, v = line.strip().partition(":")
                if k == key:
                    return v
    except FileNotFoundError:
        return None
