import json


def extract_partial_list(s, key="entities"):
    if not isinstance(s, str) or s == "":
        return []

    # remove everything before the first occurrence of the key
    field = f'"{key}":'
    s = field.join(s.split(field)[1:]).strip()
    if len(s) == 0:
        return []

    if not s.startswith("["):
        return []

    if s.endswith("},"):
        s = s[:-1]

    if not s.rstrip().endswith("}"):
        return []

    s += "]"
    try:
        return json.loads(s)
    except json.decoder.JSONDecodeError:
        return []
