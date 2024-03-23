import asyncio
import json
from logging import getLogger
from typing import AsyncGenerator

import tqdm
from pydantic import BaseModel, Field

from promptedgraphs.config import Config
from promptedgraphs.llms.chat import Chat
from promptedgraphs.llms.openai_chat import LanguageModel
from promptedgraphs.normalization.data_to_schema import data_model_to_schema

logger = getLogger(__name__)

SYSTEM_MESSAGE = """
You are a Creative Director and Ideation Specialist. Your task is brainstorm examples of objects to be passed into python's `{name}(BaseModel)` pydantic class.
Generate a list of diverse and creative examples of objects with the following fields: {label_list}

Below are definitions of each label to help aid you in creating correct examples to generate.
Assume these definitions are written by an expert and follow them closely when generating the list of examples

{label_definitions}

## Schema of the list of example data models
```json
{schema}
```

Always just return a json list of examples with no explanation.
"""

MESSAGE_TEMPLATE = """
{text}{positive_examples}{negative_examples}
Generate a list of {n} examples.

YOU MUST RETURN A JSON LIST OF EXAMPLES! Not a single example!
"""


async def brainstorming_chat(
    text: str,
    chat: Chat = None,
    positive_examples: list[str | BaseModel] = None,
    negative_examples: list[str | BaseModel] = None,
    batch_size: int = 10,
    system_message: str = SYSTEM_MESSAGE,
    **chat_kwargs,
) -> list[BaseModel] | list[str]:
    msg = MESSAGE_TEMPLATE.format(
        text=text or "",
        n=batch_size,
        positive_examples=f"\n## Good Examples:\n{positive_examples}\n"
        if positive_examples
        else "",
        negative_examples=f"\n## Bad Examples:\n{negative_examples}\n"
        if negative_examples
        else "",
    ).strip()

    # TODO replace with a tiktoken model and pad the message by 2x
    response = await chat.chat_completion(
        messages=[
            {"role": "system", "content": system_message.strip()},
            {"role": "system", "content": msg.strip()},
        ],
        **{
            **{
                "max_tokens": 4_096,
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            **chat_kwargs,
        },
    )
    # TODO check if the results stopped early, in that case, the list might be truncated
    results = json.loads(response.choices[0].message.content)
    if "items" in results:
        results = results["items"]
    return results if isinstance(results, list) else [results]


async def _brainstorm(
    text: str,
    n: int = 10,
    output_type: BaseModel | None = None,
    positive_examples: list[str | BaseModel] = None,
    negative_examples: list[str | BaseModel] = None,
    batch_size: int = 10,
    max_workers: int = 5,
    temperature: float = 0.6,
    model: str = LanguageModel.GPT35_turbo,
    config: Config = None,
) -> AsyncGenerator[BaseModel, BaseModel] | AsyncGenerator[str, str]:
    """Generate ideas using a text prompt"""
    config = config or Config()
    positive_examples = positive_examples or []
    negative_examples = negative_examples or []

    # Make a list out of the output type
    class Examples(BaseModel):
        items: list[output_type]

    schema = data_model_to_schema(Examples)

    batch_size = min(batch_size, n)

    chat = Chat(
        config=config or Config(),
        model=model,
    )

    # Format System Message
    item_schema = output_type.model_json_schema()
    labels = item_schema.get("properties", {})
    label_list = sorted(labels.keys())
    system_message = SYSTEM_MESSAGE.format(
        name=item_schema.get("title", "DataModel"),
        label_list=label_list,
        label_definitions="\n".join(
            [f" * {label}: {labels[label]}" for label in label_list]
        ),
        schema=json.dumps(schema, indent=4),
    )

    if n % batch_size != 0:
        max_workers = max(1, min(max_workers, 1 + n // batch_size))
    else:
        max_workers = max(1, min(max_workers, n // batch_size))

    async def call_brainstorming_chat():
        results = await brainstorming_chat(
            text=text,
            chat=chat,
            positive_examples=positive_examples,
            negative_examples=negative_examples,
            batch_size=batch_size,
            system_message=system_message,
            temperature=temperature,
        )
        return results

    # Create a list of coroutine objects
    tasks = [call_brainstorming_chat() for _ in range(max_workers)]

    # Use as_completed to yield from tasks as they complete
    for future in asyncio.as_completed(tasks):
        results = await future
        for result in results:
            yield result


async def generate(
    text: str,
    n: int = 10,
    output_type: type[BaseModel] | BaseModel | str | None = None,
    positive_examples: list[str | BaseModel] = None,
    negative_examples: list[str | BaseModel] = None,
    batch_size: int = 10,
    max_workers: int = 5,
    temperature: float = 0.6,
    model: str = LanguageModel.GPT35_turbo,
    config: Config = None,
) -> AsyncGenerator[BaseModel, BaseModel] | AsyncGenerator[str, str]:
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
            yield output_type(**result)
            new_yield_count += 1
            yield_count += 1
            if yield_count >= n:
                break
        if new_yield_count == 0:
            print("No more results")
            break


async def example():
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

    ideas = []
    ittr = tqdm.tqdm(total=100, desc="Brainstorming Ideas")
    async for idea in generate(
        text="Generate unique business ideas for a new startup in scuba diving sector",
        n=100,
        output_type=BusinessIdea,
        max_workers=20,
        batch_size=5,
    ):
        ideas.append(idea)
        ittr.update(1)
    return ideas


if __name__ == "__main__":
    asyncio.run(example())
