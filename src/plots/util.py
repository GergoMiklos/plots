import json
from uuid import uuid4


def generate_id():
    return str(uuid4())


def to_json(object):
    def obj_handler(obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))

    return json.dumps(object, default=obj_handler)


def get_filename(path):
    return path.split('/')[-1].split('\\')[-1].replace('.ipynb', '').replace('.py', '')


def print_module(module):
    import pprint
    pp = pprint.PrettyPrinter(depth=4)
    builtins = ['__name__', '__doc__', '__package__', '__loader__', '__spec__', '__file__', '__builtins__']
    user_data = {key: module.__dict__[key] for key in module.__dict__ if key not in builtins}
    pp.pprint(f"{user_data=}")
