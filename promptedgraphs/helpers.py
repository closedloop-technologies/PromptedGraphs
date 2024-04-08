import re


def deep_merge(d1: dict[str, any], d2: dict[str, any]):
    for k, v in d2.items():
        if k not in d1 or d1[k] is None:
            d1[k] = v
        elif isinstance(d1[k], dict) and isinstance(v, dict):
            deep_merge(d1[k], v)
        else:
            d1[k] += str(v)


def add_space_before_capital(text):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)


def camelcase_to_words(text):
    if len(text) <= 1:
        return text.replace("_", " ")
    if text.lower() == text:
        return text.replace("_", " ")
    return add_space_before_capital(text[0].upper() + text[1:]).replace("_", " ")


def format_fieldinfo(key, v: dict):
    l = f"`{key}`: {v.get('title','')} - {v.get('description','')}".strip()
    if v.get("annotation"):
        annotation = v.get("annotation")
        if annotation == "str":
            annotation = "string"
        l += f"\n\ttype: {annotation}"
    if v.get("examples"):
        l += f"\n\texamples: {v.get('examples')}"
    return l.rstrip()


def remove_nas(data: dict[str, any], nulls: list[str] = None):
    nulls = nulls or ["==NA==", "NA", "N/A", "n/a", "#N/A", "None", "none"]
    for k, v in data.items():
        if isinstance(v, dict):
            remove_nas(v)
        elif isinstance(v, list):
            for i in range(len(v)):
                if isinstance(v[i], dict):
                    remove_nas(v[i])
                elif v[i] in nulls:
                    v[i] = None
            # remove empty list items
            data[k] = [i for i in v if i is not None]
        elif v in nulls:
            data[k] = None
    return data
