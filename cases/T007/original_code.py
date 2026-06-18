def flatten_dict(d: dict, parent_key: str = '') -> dict:
    items = {}
    for k, v in d.items():
        new_key = parent_key + k if parent_key else k  # BUG
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key))
        else:
            items[new_key] = v
    return items