# Create an enum called LanguageModel with the following values: GPT2, GPT3

import asyncio

from promptedgraphs.config import Config
from promptedgraphs.llms.openai_chat import LanguageModel as OpenAILanguageModel
from promptedgraphs.llms.openai_chat import OpenAIChat

LanguageModels = OpenAILanguageModel


class Chat:
    def __init__(
        self,
        model: LanguageModels = LanguageModels.GPT35_turbo,
        config: Config = None,
        max_retries: int = 3,
        timeout=60,
        **kwargs,
    ):
        config = config or Config()
        if model in OpenAILanguageModel:
            self.chat = OpenAIChat(
                api_key=config.openai_api_key,
                model=model,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )
        else:
            raise NotImplementedError("Anthropic Model not implemented")

    async def chat_completion(self, messages: list[any] = None, **kwargs):
        return await self.chat.chat_completion(messages=messages, **kwargs)


async def usage_example():
    chat = Chat()
    messages = [
        {
            "role": "system",
            "content": "You are an expert programmer working with a user to debug and fix code. You will write the corrected code and the user provides you with traceback information after running your code on their system. A history of errors and code changes is shown in the conversation. Please fix the code and respond with the corrected code in a code block",
        },
        {
            "role": "assistant",
            "content": "```python\nprint('Hello, World!')\n```",
        },
        {
            "role": "user",
            "content": "# ERROR and STACKTRACE\n```bash\nNameError: name 'print' is not defined\n```",
        },
    ]
    print(await chat.chat_completion(messages=messages))


if __name__ == "__main__":
    asyncio.run(usage_example())
