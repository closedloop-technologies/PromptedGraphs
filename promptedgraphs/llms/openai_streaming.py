# https://github.com/openai/openai-cookbook/blob/60b12dfad1b6e7b32c4a6f1edff3b94c946b467d/examples/How_to_call_functions_with_chat_models.ipynb
import json
from collections.abc import AsyncGenerator

from httpx import AsyncClient, ReadTimeout
from sse_starlette import ServerSentEvent

from promptedgraphs.config import Config
from promptedgraphs.llms.openai_token_counter import estimate_tokens
from promptedgraphs.models import ChatFunction, ChatMessage

GPT_MODEL = "gpt-3.5-turbo-1106"
GPT_MODEL_BIG_CONTEXT = "gpt-3.5-turbo-16k-0613"


# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
async def streaming_chat_completion_request(
    messages: list[ChatMessage] | None,
    functions: list[ChatFunction] | None = None,
    model=GPT_MODEL,
    config: Config | None = None,
    temperature=0.2,
    max_tokens=4000,
    stream=True,
    timeout=None,
) -> AsyncGenerator[bytes, None]:
    assert config and config.openai_api_key is not None, "OpenAI API Key not found"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.openai_api_key}",
    }

    json_data = {
        "model": model,
        "messages": [m.model_dump(exclude_none=True) for m in messages or []],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if functions is not None and len(functions) > 0:
        json_data["functions"] = [
            f if isinstance(f, dict) else f.model_dump(exclude_none=True)
            for f in functions
        ]

    token_count_approx = estimate_tokens(json_data, model=model)

    if token_count_approx >= 4_096:
        model = GPT_MODEL_BIG_CONTEXT
        json_data["max_tokens"] = 16_384
        json_data["model"] = model
        json_data["messages"][-1]["content"] = json_data["messages"][-1][
            "content"
        ].strip()[:40_000]

    json_data["max_tokens"] = min(
        max(json_data["max_tokens"] - int(token_count_approx), 200), 16_384
    )

    async with AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=json_data)
            if response.status_code != 200:
                raise ValueError(f"Failed to post to {url}. Response: {response.text}")
            yield ServerSentEvent(
                data=json.dumps(
                    {
                        "usage": {
                            "prompt_tokens": token_count_approx,
                            "completion_tokens": 0,
                        }
                    }
                )
            )
            async for chunk in response.aiter_lines():
                if chunk.startswith("data:"):
                    yield ServerSentEvent(data=chunk[5:].strip())
                elif chunk.startswith("event:"):
                    yield ServerSentEvent(event=chunk[6:].strip())
                elif chunk.startswith("id:"):
                    yield ServerSentEvent(id=chunk[3:].strip())
                elif chunk.startswith("retry:"):
                    yield ServerSentEvent(retry=chunk[6:].strip())
                else:
                    yield ServerSentEvent(data=chunk.strip())
        except GeneratorExit:
            pass  # Handle the generator being closed, if necessary
        except ReadTimeout:
            yield ServerSentEvent(
                data="timeout: Timeout reading the response", event="error"
            )
        except Exception as e:
            yield ServerSentEvent(data=str(e), event="error")
