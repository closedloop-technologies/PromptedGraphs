def deep_merge(d1: dict[str, any], d2: dict[str, any]):
    for k, v in d2.items():
        if k not in d1 or d1[k] is None:
            d1[k] = v
        elif isinstance(d1[k], dict) and isinstance(v, dict):
            deep_merge(d1[k], v)
        else:
            d1[k] += str(v)
