import os
from enum import Enum
from logging import getLogger

import openai
from openai import AsyncOpenAI


# Language models that support json chat completions
class LanguageModel(Enum):
    GPT35_turbo = "gpt-3.5-turbo"
    GPT4 = "gpt-4-0125-preview"


class OpenAIChat:
    def __init__(self, api_key: str, model: LanguageModel, **kwargs):
        self.client = AsyncOpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            **kwargs,
        )
        self.model = model.value
        self.logger = getLogger("openai_chat")

    async def chat_completion(self, messages: list[any] = None, **kwargs) -> None:
        try:
            return await self.client.chat.completions.create(
                messages=messages or [],
                model=self.model,
                **kwargs,
            )
        except openai.APIConnectionError as e:
            self.logger.error(f"The server could not be reached: {e.__cause__}")
            raise e
        except openai.AuthenticationError as e:
            self.logger.error(f"Authentication with the OpenAI API failed: {e}")
            raise e
        except openai.RateLimitError as e:
            self.logger.error(f"Rate limit exceeded: {e}")
            raise e
        except openai.APIStatusError as e:
            self.logger.error(f"An API error occurred: {e.status_code} {e.response}")
            raise e
