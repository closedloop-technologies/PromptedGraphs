import contextlib
import json
from typing import Any, Dict, List

import tqdm
from pydantic import BaseModel, Field

from promptedgraphs.generation.data_from_model import generate
from promptedgraphs.llms.chat import Chat
from promptedgraphs.statistical.data_analysis import (
    can_cast_to_ints_without_losing_precision_np_updated,
)


class JSONSchemaTitleDescription(BaseModel):
    title: str = Field(
        title="Title",
        description="A short description of the provided schema.",
    )
    description: str = Field(
        title="Description",
        description="The concise description of the schema.",
    )


async def add_schema_titles_and_descriptions(
    schema: dict, parent_keys: list[str] = None, chat: Chat | None = None, ittr=None
):
    """Adds names and descriptions to a schema based a language model."""
    # Recursively traverse the schema and add title and descriptions
    # starting with the leaf nodes and working up to the root
    # each time adding a name and description to the schema
    if ittr is None:
        ittr = tqdm.tqdm(desc="Adding Titles and Descriptions")
    chat = chat or Chat()
    parent_keys = parent_keys or []
    if schema.get("type") == "array":
        await add_schema_titles_and_descriptions(
            schema.get("items", {}), parent_keys, chat=chat, ittr=ittr
        )
    elif schema.get("type") != "object":
        # At the leaf node no need to add a title or description
        return
    for key, value in schema.get("properties", {}).items():
        await add_schema_titles_and_descriptions(
            value, parent_keys + [key], chat=chat, ittr=ittr
        )

    # Make sure the object has a title and description
    if schema.get("title") and schema.get("description"):
        return

    prompt = """You have been tasked with adding titles and descriptions to a given JSON Schema.

    Note this object is a sub-object of a larger schema and should be named accordingly.
    It can be accessed using the following path: {parent_keys}.
    
    ## Top-level object needing a title and description
    ```json
    {schema}
    ```
    """.format(
        schema=json.dumps(schema, indent=4),
        parent_keys=".".join(parent_keys),
    )

    async for meta_data in generate(
        prompt,
        n=1,
        output_type=JSONSchemaTitleDescription,
        temperature=0.0,
        role="You are an ontologist and schema expert.",
    ):
        schema["title"] = schema.get("title") or meta_data.title
        schema["description"] = schema.get("description") or meta_data.description
        ittr.update(1)
        break


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
        return {"type": "boolean", "example": value}
    elif isinstance(value, int):
        return {"type": "integer", "example": value}
    elif isinstance(value, float):
        if can_cast_to_ints_without_losing_precision_np_updated([value]):
            return {"type": "integer", "example": value}
        return {"type": "number", "example": value}
    elif isinstance(value, str):
        with contextlib.suppress(ValueError):
            value_float = float(value)
            if can_cast_to_ints_without_losing_precision_np_updated([value]):
                return {"type": "integer", "example": int(value_float)}
            return {"type": "number", "example": value_float}
        return {"type": "string", "example": value}
    elif isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}, "example": value}
        items_type = infer_type(value[0])
        return {"type": "array", "items": items_type, "example": value}
    elif isinstance(value, dict):
        properties = {}
        example = {}
        for key, val in value.items():
            properties[key] = infer_type(val)
            example[key] = val
        return {"type": "object", "properties": properties, "example": example}
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
    type1_types = type1.get("anyOf", [type1.get("type")] if type1.get("type") else [])
    type2_types = type2.get("anyOf", [type2.get("type")] if type2.get("type") else [])

    type1_types = {
        t if isinstance(t, str) else t.get("type")
        for t in type1_types
        if isinstance(t, str) or t.get("type")
    }
    type2_types = {
        t if isinstance(t, str) else t.get("type")
        for t in type2_types
        if isinstance(t, str) or t.get("type")
    }

    # if type1 is a subtype of type2, return type2
    if type1_types.issubset(type2_types):
        type1_types = type2_types
    elif type2_types.issubset(type1_types):
        type2_types = type1_types

    if type1_types != type2_types:
        # type_diff = (type1_types - type2_types) | (type2_types - type1_types)
        # type_intersection = type1_types & type2_types
        type_union = type1_types | type2_types
        merged_example = type1.get("example", type2.get("example"))
        return {
            "anyOf": [{"type": t} for t in sorted(type_union)],
            "example": merged_example,
        }

    if "object" in type1_types:
        merged_properties = {
            **type1.get("properties", {}),
            **type2.get("properties", {}),
        }
        merged_example = type1.get("example", type2.get("example", {}))
        return {
            "type": "object",
            "properties": merged_properties,
            "example": merged_example,
        }
    elif "array" in type1_types:
        merged_items = merge_types(type1["items"], type2["items"])
        merged_example = type1.get("example", type2.get("example", []))
        return {"type": "array", "items": merged_items, "example": merged_example}
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
