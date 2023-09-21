import json

import tiktoken


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Returns the number of tokens used by a list of messages.
    See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo-0613":
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


def estimate_tokens(json_data, model="gpt-3.5-turbo-0613"):
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
