import json
import time
from logging import getLogger

import tiktoken

from promptedgraphs.llms.openai_chat import LanguageModel

logger = getLogger(__name__)


class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __init__(self, model: str, computer: str = "unknown") -> None:
        self.model = model
        self.computer = computer
        self.duration = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.start_time = time.time()

    def start(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.start_time = time.time()

    def end(self):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

    @property
    def cost(self):
        return self.llm_cost + self.compute_cost

    @property
    def llm_cost(self):
        return calculate_langage_model_costs(self, model=self.model)

    @property
    def compute_cost(self):
        return calculate_compute_costs(self, computer=self.computer)

    def dict(self):
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "duration": self.duration,
            "cost": self.cost,
            "llm_cost": self.llm_cost,
            "compute_cost": self.compute_cost,
        }

    def __repr__(self) -> str:
        return f"Usage(model={self.model}, prompt_tokens={self.prompt_tokens}, completion_tokens={self.completion_tokens}, duration={self.duration:.4f}, cost={self.cost:.6f}), compute_cost={self.compute_cost:.6f}), llm_cost={self.llm_cost:.6f})"


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


def calculate_compute_costs(usage: Usage, computer: str):
    # Pricing in dollars per 1000 tokens
    # Compute time calculated assuming AWS ondemand prices
    # t4g.medium	$0.0336	2	4 GiB	EBS Only	Up to 5 Gigabit
    default_compute_cost_second = 0.0336 / 60 / 60
    pricing = {"t4g.medium": 0.0336 / 60 / 60}
    try:
        compute_pricing = pricing[computer]
    except KeyError as e:
        logger.debug(
            f"Server {computer} not found in pricing table, using default pricing of {default_compute_cost_second:.6f}"
        )
        compute_pricing = default_compute_cost_second

    return round(usage.duration * compute_pricing, 6)


def calculate_langage_model_costs(usage: Usage, model: LanguageModel):
    # Pricing in dollars per 1000 tokenspricing = {
    pricing = {
        LanguageModel.GPT4: {
            "prompt": 0.03,
            "completion": 0.06,
        },
        LanguageModel.GPT35_turbo: {
            "prompt": 0.0010,
            "completion": 0.0020,
        },
        "default": {
            "prompt": 0.0,
            "completion": 0.0,
        },
    }

    try:
        model_pricing = pricing[model]
    except KeyError as e:
        if isinstance(model, LanguageModel):
            raise ValueError(f"Model {model} not found in pricing table") from e
        else:
            logger.warning(
                f"Model {model} not found in pricing table, using default pricing of 0"
            )
            model_pricing = pricing["default"]

    prompt_cost = usage.prompt_tokens * model_pricing["prompt"] / 1000
    completion_cost = usage.completion_tokens * model_pricing["completion"] / 1000

    total_cost = prompt_cost + completion_cost
    # round to 6 decimals
    return round(total_cost, 6)
