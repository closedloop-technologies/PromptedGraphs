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


def create_messages(text, name, labels):
    label_list = list(labels.keys())

    label_definitions = """Below are definitions of each field to help aid you in what kinds of structured data to extract for each label.
Assume these definitions are written by an expert and follow them closely.\n\n""" + "\n".join(
        [f" * {format_fieldinfo(k, dict(labels[k]))}" for k in label_list]
    )

    messages = [
        ChatMessage(
            role="system",
            content=SYSTEM_MESSAGE.format(
                name=name, label_list=label_list, label_definitions=label_definitions
            ),
        ),
        ChatMessage(role="user", content=text),
    ]

    return messages


def create_functions(is_parent_list, schema, name, description, labels, fn_name):
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
                                "properties": {
                                    k: {
                                        "type": v.get("type", "string"),
                                    }
                                    for k, v in labels.items()
                                },
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
                "properties": {
                    k: {
                        "type": v.get("type", "string"),
                    }
                    for k, v in labels.items()
                },
                "required": schema.get("required", []),
            },
        }
    ]


async def extract_data(
    text: str,
    output_type: list[BaseModel] | BaseModel,
    config: Config,
    model=GPT_MODEL,
    temperature=0.2,
):
    if is_parent_list := str(output_type).lower().startswith("list"):
        assert (
            len(output_type.__args__) == 1
        ), "Only one type argument is allowed for list types"
        output_type = output_type.__args__[0]
    assert issubclass(output_type, BaseModel), "output_type must be a Pydantic model"

    schema = output_type.model_json_schema()
    name = schema["title"]
    description = schema["description"]
    labels = schema["properties"]
    fn_name = camelcase_to_words(name).replace(" ", "_").lower()

    messages = create_messages(text, name, labels)
    functions = create_functions(
        is_parent_list, schema, name, description, labels, fn_name
    )

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
                        yield output_type(**data)
                else:
                    data = json.loads(payload)
                    yield output_type(**data)
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
                yield output_type(**data)

            count = len(s)
