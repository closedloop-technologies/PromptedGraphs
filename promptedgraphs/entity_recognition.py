"""This module contains the entity recognition pipeines
We can rely on the spacy library for this task as well
as their spacy-llm library for the language model.

We will be providing a custom implementation of spacy-llm
in order to support the streaming responses from the API
and will still make the results play well with spacy to enable
custom training and other features.

Ideally ER should be done locally with a transformer-style
model trained on a given domain.  Until we get there,
we will use LLMs to label the data.

Base case:
 * Run entity recognition on the text, stream back spacy-compatible entity spans

Nice to have
 * Run ER multiple times with noise and only choose a subset of labels
 * Aggregate the highest confidence common labels

Ideal case:
 * For labels with high disagreement, have a human label the data
 * Create a gold-star dataset for training a custom model
 * Train a custom model on the data
 * Evaluate the performance of the model and compare to the LLM in performance, cost and time

"""


import contextlib
import json
import re

import tiktoken

from promptedgraphs.config import Config
from promptedgraphs.llms.openai_streaming import (
    GPT_MODEL,
    streaming_chat_completion_request,
)
from promptedgraphs.llms.openai_token_counter import Usage
from promptedgraphs.models import ChatMessage, EntityReference
from promptedgraphs.parsers import extract_partial_list

# Name and description of entity types


SYSTEM_MESSAGE = """
You are an expert Named Entity Recognition (NER) system.
Your task is to accept Text as input and extract named entities to be passed to the `{name}` function.

Entities must have one of the following labels: {label_list}.
If a span is not an entity label it: `==NONE==`.

{label_definitions}
"""


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


async def extract_entities(
    text: str,
    labels: dict[str, str],
    config: Config,
    name="entities",
    description: str | None = "Extract Entities from text",
    include_reason=True,
    model=GPT_MODEL,
    temperature=0.2,
):
    label_list = sorted(labels.keys())
    messages = build_message_list(
        text,
        label_list,
        labels=labels,
        name=f"extract_{name}".lower().replace(" ", "_"),
    )

    functions = build_function_spec(
        label_list,
        function_name=f"extract_{name}".lower().replace(" ", "_"),
        key=name,
        description=description,
        include_reason=include_reason,
    )

    count = 0
    payload = ""
    usage = Usage(model=model)
    usage.start()
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
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            usage.completion_tokens += len(encoding.encode(payload))
            with contextlib.suppress(json.decoder.JSONDecodeError):
                s = json.loads(payload).get(name, [])
                for entity in _format_entities(s[count:], text):
                    yield entity

            break

        # TODO try catch for malformed json
        data = json.loads(msg.data)

        msg_usage = data.get("usage")
        if msg_usage is not None:
            usage.prompt_tokens += msg_usage.get("prompt_tokens", 0)
            usage.completion_tokens += msg_usage.get("completion_tokens", 0)

        choices = data.get("choices")
        if choices is None:
            continue

        delta = choices[0].get("delta")

        # TODO rewrite this to be more robust streaming json parser
        payload += delta.get("function_call", {}).get("arguments", "")
        s = extract_partial_list(payload, key=name)
        if s is None or len(s) == 0 or len(s) <= count:
            continue

        for entity in _format_entities(s[count:], text):
            yield entity
        count = len(s)

    usage.end()  # calculates cost and time
    yield usage
