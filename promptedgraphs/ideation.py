import asyncio
import contextlib
import json

from pydantic import BaseModel, Field

from promptedgraphs.config import Config
from promptedgraphs.data_extraction import (
    camelcase_to_words,
    create_functions,
    format_fieldinfo,
    remove_nas,
)
from promptedgraphs.llms.openai_streaming import (
    GPT_MODEL,
    streaming_chat_completion_request,
)
from promptedgraphs.models import ChatMessage
from promptedgraphs.parsers import extract_partial_list

BRAINSTORM_SYSTEM_MESSAGE = """
You are a Creative Director and Ideation Specialist. Your task is brainstorm examples of objects to be passed into python's `{name}(BaseModel)` pydantic class.
Generate {count} examples of objects that fit the following fields: {label_list}

{label_definitions}

{positive_examples}

{negative_examples}
"""


def create_messages(
    text,
    name,
    labels,
    n=10,
    positive_examples=None,
    negative_examples=None,
    custom_system_message=None,
    **kwargs,
):
    messages = []
    if custom_system_message:
        messages.append(
            ChatMessage(
                role="system",
                content=custom_system_message.strip(),
            )
        )
    else:
        label_list = list(labels.keys())

        label_definitions = """Below are definitions of each field to help aid you in what kinds of structured data to extract for each label.
    Assume these definitions are written by an expert and follow them closely.\n\n""" + "\n".join(
            [f" * {format_fieldinfo(k, dict(labels[k]))}" for k in label_list]
        )

        custom_system_message = BRAINSTORM_SYSTEM_MESSAGE.format(
            name=name,
            label_list=label_list,
            label_definitions=label_definitions,
            count=n,
            positive_examples="Good Examples:\n{positive_examples}\n"
            if positive_examples
            else "",
            negative_examples="Bad Examples:\n{negative_examples}\n"
            if negative_examples
            else "",
            **kwargs,
        )
        messages.append(
            ChatMessage(
                role="system",
                content=custom_system_message.strip(),
            )
        )
    if text:
        messages.append(ChatMessage(role="user", content=text))

    return messages


async def streaming_chat_wrapper(
    messages,
    functions,
    model,
    config,
    temperature,
    output_type,
    is_parent_list,
    name,
):
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
            fn_name = camelcase_to_words(name).replace(" ", "_").lower()
            s = extract_partial_list(payload, key=fn_name)
            if s is None or len(s) == 0 or len(s) <= count:
                continue

            for data in s[count:]:
                yield output_type(**remove_nas(data))

            count = len(s)


async def parallelize_streaming_chat_wrapper(
    num_workers,
    messages,
    functions,
    model,
    config,
    temperature,
    output_type,
    is_parent_list,
    name,
):
    print(f"parallelize_streaming_chat_wrapper {num_workers}")

    async def collect_results(generator):
        results = []
        async for item in generator:
            results.append(item)
        return results

    tasks = [
        asyncio.ensure_future(
            collect_results(
                streaming_chat_wrapper(
                    messages,
                    functions,
                    model,
                    config,
                    temperature,
                    output_type,
                    is_parent_list,
                    name,
                )
            )
        )
        for _ in range(num_workers)
    ]

    for future in asyncio.as_completed(tasks):
        results = await future
        for result in results:
            yield result


async def _brainstorm(
    text: str,
    n: int = 10,
    temperature: float = 0.2,
    output_type: type[BaseModel] | BaseModel | str | None = None,
    positive_examples: list[str | BaseModel] = None,
    negative_examples: list[str | BaseModel] = None,
    batch_size: int = 10,
    max_workers: int = 5,
    model: str = GPT_MODEL,
    config: Config = None,
) -> list[BaseModel] | list[str]:
    """Generate ideas using a text prompt"""
    config = config or Config()
    positive_examples = positive_examples or []
    negative_examples = negative_examples or []
    output_type = output_type or str

    if is_parent_list := str(output_type).lower().startswith("list"):
        assert (
            len(output_type.__args__) == 1
        ), "Only one type argument is allowed for list types"
        output_type = output_type.__args__[0]
    assert issubclass(output_type, BaseModel), "output_type must be a Pydantic model"

    schema = output_type.model_json_schema()
    name = schema["title"]

    batch_size = min(batch_size, n)

    messages = create_messages(
        text,
        name=name,
        labels=schema["properties"],
        n=batch_size,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
    )
    functions = create_functions(
        is_parent_list,
        schema,
        fn_name=camelcase_to_words(name).replace(" ", "_").lower(),
    )

    if n % batch_size != 0:
        max_workers = max(1, min(max_workers, 1 + n // batch_size))
    else:
        max_workers = max(1, min(max_workers, n // batch_size))

    yield_count = 0
    if max_workers == 1:
        results = streaming_chat_wrapper(
            messages,
            functions,
            model,
            config,
            temperature,
            output_type,
            is_parent_list,
            name,
        )
    else:
        results = parallelize_streaming_chat_wrapper(
            max_workers,
            messages,
            functions,
            model,
            config,
            temperature,
            output_type,
            is_parent_list,
            name,
        )
    async for result in results:
        yield result
        yield_count += 1
        if yield_count >= n:
            break


async def brainstorm(
    text: str,
    n: int = 10,
    temperature: float = 0.2,
    output_type: type[BaseModel] | BaseModel | str | None = None,
    positive_examples: list[str | BaseModel] = None,
    negative_examples: list[str | BaseModel] = None,
    batch_size: int = 10,
    max_workers: int = 5,
    model: str = GPT_MODEL,
    config: Config = None,
) -> list[BaseModel] | list[str]:
    yield_count = 0
    while yield_count < n:
        new_yield_count = 0
        async for result in _brainstorm(
            text,
            n=n - yield_count,
            temperature=temperature,
            output_type=output_type,
            positive_examples=positive_examples,
            negative_examples=negative_examples,
            batch_size=batch_size,
            max_workers=max_workers,
            model=model,
            config=config,
        ):
            yield result
            new_yield_count += 1
            yield_count += 1
            if yield_count >= n:
                break
        if new_yield_count == 0:
            print("No more results")
            break


class BusinessIdea(BaseModel):
    """A business idea generated using the Jobs-to-be-done framework
    For example "We help [adj] [target_audience] do [action] so they can [benefit or do something else]"
    """

    target_audience: str = Field(title="Target Audience")
    action: str = Field(title="Action")
    benefit: str = Field(title="Benefit or next action")
    adj: str | None = Field(
        title="Adjective",
        description="Optional adjective describing the target audience's condition",
    )
