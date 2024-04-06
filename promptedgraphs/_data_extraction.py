"""The purpose of this class is to extract data from text
and return it as a structured object or a list of structured objects.

Base case:
 * Provide text and specify the return type as a Pydantic model and it returns an instance of that model

"""

from promptedgraphs.helpers import camelcase_to_words, format_fieldinfo
from promptedgraphs.models import ChatMessage

SYSTEM_MESSAGE = """
You are a Qualitative User Researcher and Linguist. Your task is to extract structured data from text to be passed into python's `{name}(BaseModel)` pydantic class.
Maintain as much verbatim text as possible, light edits are allowed, feel free to remove any text that is not relevant to the label.
If there is not information applicable for a particular field, use the value `==NA==`.

In particular look for the following fields: {label_list}.

{label_definitions}
"""



def create_messages(text, name, labels, custom_system_message=None):
    label_list = list(labels.keys())

    label_definitions = """Below are definitions of each field to help aid you in what kinds of structured data to extract for each label.
Assume these definitions are written by an expert and follow them closely.\n\n""" + "\n".join(
        [f" * {format_fieldinfo(k, dict(labels[k]))}" for k in label_list]
    )

    custom_system_message = custom_system_message or SYSTEM_MESSAGE.format(
        name=name, label_list=label_list, label_definitions=label_definitions
    )

    messages = [
        ChatMessage(
            role="system",
            content=custom_system_message,
        )
    ]
    if text:
        messages.append(ChatMessage(role="user", content=text))

    return messages


def format_properties(properties, refs=None):
    refs = refs or {}
    d = {}
    for k, v in properties.items():
        dtypes = None  # reset per loop
        dtype = v.get("type")
        if dtype is None and v.get("anyOf"):
            dtypes = [t for t in v["anyOf"] if t["type"] != "null"]
            if len(dtypes):
                dtype = dtypes[0]["type"]
        d[k] = {"type": dtype or "string"}
        if d[k]["type"] == "array":
            d[k][
                "description"
            ] = f"{v.get('title','')} - {v.get('description', '')}".strip()

            if reference := v.get("items", {}).get("$ref", "/").split("/")[-1]:
                v2 = refs[reference]
            elif dtypes:
                v2 = dtypes[0].get("items", v)
            else:
                v2 = v

            item_type = v2.get("type")
            if item_type == "object":
                d[k]["items"] = {
                    "type": v2.get("type", "object"),
                    "description": f"{v2.get('title','')} - {v2.get('description', '')}".strip(),
                    "properties": format_properties(v2.get("properties", {})),
                    "required": v2.get("required", []),
                }
            else:
                d[k]["items"] = {"type": item_type}
    return d


def create_functions(is_parent_list, schema, fn_name: str = None):
    """Note the top level cannot be an array, only nested objects can be arrays"""
    name, description = (
        schema["title"],
        schema["description"],
    )
    fn_name = fn_name or camelcase_to_words(name).replace(" ", "_").lower()
    if is_parent_list:
        return [
            {
                "name": name,
                "type": "function",
                "description": "Extract a non-empty list of structured data from text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        fn_name: {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "description": description,
                                "properties": format_properties(
                                    schema["properties"], refs=schema.get("$defs", {})
                                ),
                                "required": schema.get("required", []),
                            },
                        }
                    },
                },
            }
        ]

    return [
        {
            "name": name,
            "type": "function",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": format_properties(
                    schema["properties"], refs=schema.get("$defs", {})
                ),
                "required": schema.get("required", []),
            },
        }
    ]

