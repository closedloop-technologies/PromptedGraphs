"""The purpose of this class is to extract data from text
and return it as a structured object or a list of structured objects.

Base case:
 * Provide text and specify the return type as a Pydantic model and it returns an instance of that model

"""


import contextlib
import json
import re

from pydantic import BaseModel

from promptedgraphs.config import Config
from promptedgraphs.llms.openai_streaming import (
    GPT_MODEL,
    streaming_chat_completion_request,
)
from promptedgraphs.models import ChatMessage
from promptedgraphs.parsers import extract_partial_list

SYSTEM_MESSAGE = """
You are a Qualitative User Researcher and Linguist. Your task is to extract structured data from text to be passed into python's `{name}(BaseModel)` pydantic class.
Maintain as much verbatim text as possible, light edits are allowed, feel free to remove any text that is not relevant to the label.
If there is not information applicable for a particular field, use the value `==NA==`.

In particular look for the following fields: {label_list}.

{label_definitions}
"""


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


async def extract_data(
    text: str,
    output_type: list[BaseModel] | BaseModel,
    config: Config,
    model=GPT_MODEL,
    temperature=0.0,
    custom_system_message: str | None = None,
):
    if is_parent_list := str(output_type).lower().startswith("list"):
        assert (
            len(output_type.__args__) == 1
        ), "Only one type argument is allowed for list types"
        output_type = output_type.__args__[0]
    assert issubclass(output_type, BaseModel), "output_type must be a Pydantic model"

    schema = output_type.model_json_schema()
    name = schema["title"]
    fn_name = camelcase_to_words(schema["title"]).replace(" ", "_").lower()

    messages = create_messages(
        text,
        schema["title"],
        schema["properties"],
        custom_system_message=custom_system_message,
    )
    functions = create_functions(is_parent_list, schema, fn_name)

    count = 0
    payload = ""
    async for msg in streaming_chat_completion_request(
        messages=messages,
        functions=functions,
        model=model,
        config=config,
        temperature=temperature,
    ):
        if msg.data is None or msg.data == "":
            continue

        if msg.data == "[DONE]":
            with contextlib.suppress(json.decoder.JSONDecodeError):
                if is_parent_list:
                    s = json.loads(payload).get(name, [])
                    for data in s[count:]:
                        yield output_type(**remove_nas(data))
                else:
                    data = json.loads(payload)
                    yield output_type(**remove_nas(data))
            break

        # TODO try catch for malformed json
        if msg.event == "error":
            print("ERROR", msg.data)
            break

        data = json.loads(msg.data)

        choices = data.get("choices")
        if choices is None:
            continue

        delta = choices[0].get("delta")

        # TODO rewrite this to be more robust streaming json parser
        payload += delta.get("function_call", {}).get("arguments", "")

        if is_parent_list:
            s = extract_partial_list(payload, key=fn_name)
            if s is None or len(s) == 0 or len(s) <= count:
                continue

            for data in s[count:]:
                yield output_type(**remove_nas(data))

            count = len(s)
