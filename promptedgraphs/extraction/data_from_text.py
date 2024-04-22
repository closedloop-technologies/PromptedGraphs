import asyncio
import json
from logging import getLogger
from typing import AsyncGenerator

from pydantic import BaseModel

from promptedgraphs.config import Config, load_config
from promptedgraphs.generation.schema_from_model import schema_from_model
from promptedgraphs.llms.chat import Chat
from promptedgraphs.llms.openai_chat import LanguageModel
from promptedgraphs.llms.usage import Usage
from promptedgraphs.models import ChatMessage

logger = getLogger(__name__)

SYSTEM_MESSAGE = """
You are an information extraction expert.
Your task is to extract structured information from the provided text.
The extracted data should fit the provided schema to structure the data into a Pydantic BaseModel class.
Do not create data and lightly edit and reformat data to match the schema.

Assume this schema was written by an expert and follow them closely when extracting the data from the text.
Return a list of extracted data that fits the schema
Always prefer a list of similar items over a single complex item.

## {name}(BaseModel) Schema:
{description}

{label_definitions}

## Schema of the list of data to extract
```json
{schema}
```

Always just return a json list of the extracted data with no explanation.
"""

MESSAGE_TEMPLATE = """
## Extract data from this text:

{text}

## JSON list of extracted data
"""


async def extraction_chat(
    text: str,
    chat: Chat = None,
    system_message: str = SYSTEM_MESSAGE,
    message_template: str = MESSAGE_TEMPLATE,
    usage: Usage = None,
    message_history: list[ChatMessage] = None,
    force_json: bool = True,
    **chat_kwargs,
) -> list[BaseModel] | list[str]:
    usage = usage or Usage()

    messages = [{"role": "system", "content": system_message.strip()}]
    messages.extend(message_history or [])
    messages.append(
        {"role": "user", "content": message_template.format(text=text or "").strip()}
    )
    # TODO replace with a tiktoken model and pad the message by 2x
    default_chat_args = {
        "max_tokens": 4_096,
        "temperature": 0.0,
    }
    if force_json:
        default_chat_args["response_format"] = {"type": "json_object"}

    response = await chat.chat_completion(
        messages=messages, **default_chat_args | chat_kwargs
    )
    if hasattr(response, "usage"):
        usage.completion_tokens = getattr(response.usage, "completion_tokens") or 0
        usage.prompt_tokens = getattr(response.usage, "prompt_tokens") or 0

    # TODO check if the results stopped early, in that case, the list might be truncated
    if force_json:
        results = json.loads(response.choices[0].message.content)
    else:
        content = response.choices[0].message.content
        # TODO this will break if multiple json objects are in the response
        results = json.loads(content.split("```json")[1].split("```")[0])

    if "items" in results:
        results = results["items"]
    return results if isinstance(results, list) else [results]


async def _extract_data_from_text(
    text: str,
    output_type: BaseModel | None = None,
    temperature: float = 0.0,
    model: str = LanguageModel.GPT35_turbo,
    config: Config = None,
    usage: Usage = None,
) -> AsyncGenerator[BaseModel, BaseModel] | AsyncGenerator[str, str]:
    """Generate ideas using a text prompt"""

    if output_type is None:
        raise ValueError("output_type must be provided")

    usage = usage or Usage(model)

    # Make a list out of the output type
    class StructuredData(BaseModel):
        items: list[output_type]

    schema = schema_from_model(StructuredData)

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
        description=item_schema.get("description", ""),
        label_definitions="\n".join(
            [f" * {label}: {labels[label]}" for label in label_list]
        ),
        schema=json.dumps(schema, indent=4),
    )

    # async def call_brainstorming_chat():
    results = await extraction_chat(
        text=text,
        chat=chat,
        system_message=system_message,
        temperature=temperature,
        usage=usage,
    )
    for result in results:
        yield result


async def data_from_text(
    text: str,
    output_type: type[BaseModel] | BaseModel | str | None = None,
    temperature: float = 0.0,
    model: str = LanguageModel.GPT35_turbo,
    config: Config = None,
    usage: Usage = None,
) -> AsyncGenerator[BaseModel, BaseModel] | AsyncGenerator[str, str]:
    usage = usage or Usage(model)
    async for result in _extract_data_from_text(
        text,
        temperature=temperature,
        output_type=output_type,
        model=model,
        config=config,
        usage=usage,
    ):
        # TODO heal the data if it cannot be parsed
        if not result:
            continue
        yield output_type(**result)


async def example():
    from pydantic import BaseModel, Field

    class UserIntent(BaseModel):
        """The UserIntent entity, representing the canonical description of what a user desires to achieve in a given conversation."""

        intent_name: str = Field(
            title="Intent Name",
            description="Canonical name of the user's intent",
            examples=[
                "question",
                "command",
                "clarification",
                "chit_chat",
                "greeting",
                "feedback",
                "nonsensical",
                "closing",
                "harrassment",
                "unknown",
            ],
        )
        description: str | None = Field(
            title="Intent Description",
            description="A detailed explanation of the user's intent",
        )

    load_config()

    msg = """How can I learn more about your product?"""
    async for intent in data_from_text(
        text=msg, output_type=UserIntent, config=Config()
    ):
        print(intent)


if __name__ == "__main__":
    asyncio.run(example())
