# utils/flatten_utils.py

def flatten_json(y, prefix='', max_list_elements=10):
    out = {}

    def flatten(x, name=''):
        if isinstance(x, dict):
            for key in x:
                flatten(x[key], f"{name}{key}_")
        elif isinstance(x, list):
            for i, item in enumerate(x[:max_list_elements]):
                flatten(item, f"{name}{i}_")
        else:
            out[name[:-1]] = x  # Remove the trailing '_'

    flatten(y, prefix)
    return out
