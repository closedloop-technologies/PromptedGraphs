import json
import re

from promptedgraphs.config import Config, load_config
from promptedgraphs.llms.openai_streaming import (
    GPT_MODEL,
    streaming_chat_completion_request,
)


async def _sync_wrapper(messages, config: Config | None = None, model=GPT_MODEL):
    payload = ""
    async for event in streaming_chat_completion_request(
        messages=messages,
        functions=None,
        config=config or load_config(),
        stream=False,
        model=model,
    ):
        if event.data:
            payload += event.data
        elif event.retry:
            print(f"Retry: {event.retry}")
    data = json.loads(payload)
    return data


def extract_code_blocks(text: str) -> list[dict[str, str]]:
    pattern = re.compile(r"```(.*?)\n(.*?)```", re.DOTALL)
    matches = pattern.findall(text)

    blocks = []
    for match in matches:
        block_type, content = match
        blocks.append({"block_type": block_type.strip(), "content": content.strip()})
    return blocks
