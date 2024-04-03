from typing import Any, Dict, List

from promptedgraphs.statistical.data_analysis import (
    can_cast_to_ints_without_losing_precision_np_updated,
)


def schema_from_data(data_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates a minimal schema based on provided data samples.

    Args:
        data_samples (List[dict]): A list of data samples to generate the schema from.

    Returns:
        dict: The generated minimal schema as a dictionary.
    """
    if not data_samples:
        return {}

    schema: Dict[str, Any] = {"type": "object", "properties": {}}
    required_keys = set(data_samples[0].keys())

    for sample in data_samples:
        required_keys &= set(sample.keys())
        for key, value in sample.items():
            if key in schema["properties"]:
                schema["properties"][key] = merge_types(
                    schema["properties"][key], infer_type(value)
                )
            else:
                schema["properties"][key] = infer_type(value)

    schema["required"] = sorted(required_keys)

    return schema


def infer_type(value: Any) -> Dict[str, Any]:
    """Infers the type of a value and returns the corresponding schema.

    Args:
        value: The value to infer the type from.

    Returns:
        dict: The inferred schema for the value.
    """
    if isinstance(value, bool):
        return {"type": "boolean"}
    elif isinstance(value, int) or can_cast_to_ints_without_losing_precision_np_updated(
        [value]
    ):
        return {"type": "integer"}
    elif isinstance(value, float):
        return {"type": "number"}
    elif isinstance(value, str):
        return {"type": "string"}
    elif isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}
        items_type = infer_type(value[0])
        return {"type": "array", "items": items_type}
    elif isinstance(value, dict):
        properties = {}
        required = []
        for key, val in value.items():
            properties[key] = infer_type(val)
            required.append(key)
        return {"type": "object", "properties": properties}
    else:
        return {}


def merge_types(type1: Dict[str, Any], type2: Dict[str, Any]) -> Dict[str, Any]:
    """Merges two types to ensure the resulting type is the minimal union of the types found.

    Args:
        type1 (dict): The first type to merge.
        type2 (dict): The second type to merge.

    Returns:
        dict: The merged type.
    """
    if type1["type"] != type2["type"]:
        return {"anyOf": [type1, type2]}
    if type1["type"] == "object":
        merged_properties = {
            **type1.get("properties", {}),
            **type2.get("properties", {}),
        }
        return {"type": "object", "properties": merged_properties}
    elif type1["type"] == "array":
        merged_items = merge_types(type1["items"], type2["items"])
        return {"type": "array", "items": merged_items}
    else:
        return type1


def example():
    data_samples = [
        {"name": "Alice", "age": 30, "is_student": False},
        {"name": "Bob", "is_student": True},
    ]
    schema = schema_from_data(data_samples)
    print(schema)


if __name__ == "__main__":
    example()
