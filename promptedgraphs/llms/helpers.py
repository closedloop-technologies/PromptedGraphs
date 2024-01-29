import json
import re
import time

from promptedgraphs.config import Config, load_config
from promptedgraphs.llms.openai_streaming import (
    GPT_MODEL,
    streaming_chat_completion_request,
)


async def _sync_wrapper(
    messages, config: Config | None = None, model=GPT_MODEL, retry_counter=3, **kwargs
):
    payload = ""
    async for event in streaming_chat_completion_request(
        messages=messages,
        functions=None,
        config=config or load_config(),
        stream=False,
        model=model,
        **kwargs,
    ):
        if event.data:
            payload += event.data
        elif event.retry:
            print(f"Retry: {event.retry}")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        if "context_length_exceeded" in payload:
            kwargs["max_tokens"] = 40000
            return await _sync_wrapper(
                messages,
                config=config,
                model="gpt-4-1106-preview",
                retry_counter=retry_counter,
                **kwargs,
            )
        if (
            "Server disconnected without sending a response." in payload
            and retry_counter > 0
        ):
            time.sleep(3)
            return await _sync_wrapper(
                messages,
                config=config,
                model=model,
                retry_counter=retry_counter - 1,
                **kwargs,
            )
        raise e
    return data


def extract_code_blocks(text: str) -> list[dict[str, str]]:
    code_block_terminators = re.compile(r"```", re.DOTALL)
    num_code_block_terminators = len(code_block_terminators.findall(text))
    if num_code_block_terminators % 2 == 1:
        text += "\n```"

    pattern = re.compile(r"```(.*?)\n(.*?)```", re.DOTALL)
    matches = pattern.findall(text)

    blocks = []
    for match in matches:
        block_type, content = match
        blocks.append({"block_type": block_type.strip(), "content": content.strip()})
    return blocks
