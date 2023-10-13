# get traceback

from promptedgraphs.llms.helpers import _sync_wrapper, extract_code_blocks
from promptedgraphs.models import ChatMessage


async def fix_code(
    code: str, error: str, tb: str, history: list[tuple[str, str]]
) -> tuple[str, list[tuple[str, str]]]:
    """return new code plus history of code, tb pairs"""

    system_message = """You are an expert programmer working with a user to debug and fix code
    you will write the corrected code and the user provides you with traceback information
    after running your code on their system.

    A history of errors and code changes is shown in the conversation.  Please fix the code
    and respond with the corrected code in a code block"""

    history = history or []
    history.append((code, f"{error}\n\n{tb}" if error else tb or ""))

    messages = [
        ChatMessage(
            role="system",
            content=system_message,
        )
    ]
    for c, err in history:
        messages.append(
            ChatMessage(
                role="assistant",
                content=f"```python\n{c}\n```",
            )
        )
        messages.append(
            ChatMessage(
                role="user",
                content=f"# ERROR and STACKTRACE\n```bash\n{err}\n```",
            )
        )
    data = await _sync_wrapper(messages, model="gpt-4-0613")

    # pull out the json and pydantic code blocks
    content = data.get("choices")[0]["message"]["content"]
    results = extract_code_blocks(content)
    for r in results:
        if r["block_type"] == "python":
            return r["content"], history
