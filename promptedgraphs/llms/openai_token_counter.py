import json
import time

import tiktoken


class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __init__(self, model: str) -> None:
        self.model = model

    def start(self):
        self.cost = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.start_time = time.time()

    def end(self):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.cost = openai_api_calculate_cost(self, model=self.model)

    def dict(self):
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "duration": self.duration,
            "cost": self.cost,
        }

    def __repr__(self) -> str:
        return f"Usage(model={self.model}, prompt_tokens={self.prompt_tokens}, completion_tokens={self.completion_tokens}, duration={self.duration:.4f}, cost={self.cost:.6f})"


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-1106"):
    """Returns the number of tokens used by a list of messages.
    See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo-1106":
        num_tokens = 0
        for message in messages:
            num_tokens += (
                4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            )
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    else:
        encoding = tiktoken.encoding_for_model(model)
        return len(
            encoding.encode(
                "<|endoftext|>".join(
                    [l for m in messages for l in m.values() if l is not None]
                ),
                allowed_special=set(encoding._special_tokens.keys()),
            )
        )


def estimate_tokens(json_data, model="gpt-3.5-turbo-1106"):
    # Adjust max_tokens based on message length and function length
    message_tokens = num_tokens_from_messages(
        json_data.get("messages", []), model=model
    )

    encoding = tiktoken.encoding_for_model(model)
    function_tokens = len(
        encoding.encode(
            "<|endoftext|>".join(
                [
                    json.dumps(l)
                    for m in json_data.get("functions", [])
                    for l in m.values()
                    if l is not None
                ]
            ),
            allowed_special=set(encoding._special_tokens.keys()),
        )
    )
    return function_tokens + message_tokens


def openai_api_calculate_cost(usage: Usage, model="gpt-4-1106-preview"):
    # Pricing in dollars per 1000 tokenspricing = {
    pricing = {
        "gpt-4-0125-preview": {
            "prompt": 0.01,
            "completion": 0.03,
        },
        "gpt-4-1106-preview": {
            "prompt": 0.01,
            "completion": 0.03,
        },
        "gpt-4-1106-vision-preview": {
            "prompt": 0.01,
            "completion": 0.03,
        },
        "gpt-4": {
            "prompt": 0.03,
            "completion": 0.06,
        },
        "gpt-4-32k": {
            "prompt": 0.06,
            "completion": 0.12,
        },
        "gpt-3.5-turbo-1106": {
            "prompt": 0.0010,
            "completion": 0.0020,
        },
        "gpt-3.5-turbo-instruct": {
            "prompt": 0.0015,
            "completion": 0.0020,
        },
        "davinci-002": {
            "prompt": 0.0020,
            "completion": 0.0020,  # No separate completion price listed
        },
        "babbage-002": {
            "prompt": 0.0004,
            "completion": 0.0004,  # No separate completion price listed
        },
    }

    try:
        model_pricing = pricing[model]
    except KeyError:
        return 0

    prompt_cost = usage.prompt_tokens * model_pricing["prompt"] / 1000
    completion_cost = usage.completion_tokens * model_pricing["completion"] / 1000

    total_cost = prompt_cost + completion_cost
    # round to 6 decimals
    return round(total_cost, 6)
