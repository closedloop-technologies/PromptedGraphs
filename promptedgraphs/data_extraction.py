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
from promptedgraphs.models import ChatMessage, EntityReference
from promptedgraphs.parsers import extract_partial_list

# Name and description of entity types


SYSTEM_MESSAGE = """
You are a Qualitative User Researcher and Linguist, skilled in analyzing and interpreting human behavior and language.
With your methodical approach and keen observational skills, you effectively uncover user motivations and preferences.
Your linguistic expertise allows you to grasp language nuances, ensuring accurate interpretation of user feedback.
Your analytical, detail-oriented, and systematic nature makes you an invaluable asset in improving user experiences.

Your task is to extract structured data from text to be passed into python's `{name}(BaseModel)` pydantic class.
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


def build_message_list(
    text: str,
    label_list: list[str],
    labels: dict[str, str],
    name="extract_entities",
):
    label_definitions = """Below are definitions of each label to help aid you in what kinds of named entities to extract for each label.
Assume these definitions are written by an expert and follow them closely.\n\n""" + "\n".join(
        [f" * {label}: {labels[label]}" for label in label_list]
    )

    return [
        ChatMessage(
            role="system",
            content=SYSTEM_MESSAGE.format(
                name=name, label_list=label_list, label_definitions=label_definitions
            ),
        ),
        ChatMessage(role="user", content=text),
    ]


def build_function_spec(
    label_list: list[str],
    function_name="extract_entities",
    key="entities",
    description="",
    include_reason=True,
):
    spec = [
        {
            "name": function_name,
            "type": "function",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    key: {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "description": "The raw text and label for each entity occurrence",
                            "properties": {
                                "text_span": {
                                    "type": "string",
                                    "description": "The exact text of referenced entity.",
                                },
                                "is_entity": {
                                    "type": "boolean",
                                    "description": "A boolean indicating if the span is an entity label.",
                                },
                                "label": {
                                    "type": "string",
                                    "enum": label_list + ["==NONE=="],
                                    "description": "The label of the entity.",
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "A short description of why that label was selected.",
                                },
                            },
                            "required": ["text_span", "is_entity", "label", "reason"],
                        },
                    }
                },
            },
        }
    ]
    if not include_reason:
        spec[0]["parameters"]["properties"][key]["items"]["properties"].pop("reason")
        spec[0]["parameters"]["properties"][key]["items"]["required"] = [
            "text_span",
            "is_entity",
            "label",
        ]
    return spec


def _format_entities(s, text):
    for entity in s:
        if entity["is_entity"]:
            for match in re.finditer(entity["text_span"], text):
                yield EntityReference(
                    start=match.start(),
                    end=match.end(),
                    text=entity["text_span"],
                    label=entity["label"],
                    reason=entity.get("reason"),
                )


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
    print("TODO handle is_parent_list", is_parent_list)
    assert issubclass(output_type, BaseModel), "output_type must be a Pydantic model"
    schema = output_type.model_json_schema()

    name = schema["title"]
    description = schema["description"]
    labels = schema["properties"]

    def format_fieldinfo(key, v: dict):
        l = f"`{key}`: {v.get('title','')} - {v.get('description','')}".strip()
        if v.get("annotation"):
            l += f"\n\ttype: {v.get('annotation')}"
        if v.get("examples"):
            l += f"\n\texamples: {v.get('examples')}"
        return l.rstrip()

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

    fn_name = camelcase_to_words(name).replace(" ", "_").lower()

    functions = [
        {
            "name": name,
            "type": "function",
            "description": "A list of structured data extracted from text",
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
                                    "type": v.get("type", "str"),
                                    "description": f"{v.get('title','')} - {v.get('description')}",
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
                s = json.loads(payload).get(name, [])
                for entity in _format_entities(s[count:], text):
                    yield entity

            break

        # TODO try catch for malformed json
        data = json.loads(msg.data)

        choices = data.get("choices")
        if choices is None:
            continue

        delta = choices[0].get("delta")

        # TODO rewrite this to be more robust streaming json parser
        payload += delta.get("function_call", {}).get("arguments", "")
        s = extract_partial_list(payload, key=fn_name)
        if s is None or len(s) == 0 or len(s) <= count:
            continue

        for entity in _format_entities(s[count:], text):
            yield entity
        count = len(s)
