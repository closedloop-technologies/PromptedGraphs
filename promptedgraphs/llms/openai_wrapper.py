from langchain.chat_models import ChatOpenAI


def call_default_llm(
    prompt,
    temperature=0.2,
    max_tokens=3000,
    request_timeout=180,
    model_name="gpt-3.5-turbo-0613",
):
    default_llm = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "request_timeout": request_timeout,
    }
    llm = ChatOpenAI(model_name=model_name, **default_llm)
    return llm.call_as_llm(prompt) if hasattr(llm, "call_as_llm") else llm(prompt)


def intersection(lst1, lst2):
    return [value for value in lst1 if value in lst2]


# TODO move this to promptedgraph


def gpt_fix_json(text: str, error: str) -> str:
    prompt = f"""Fix the following JSON.  Return the fixed JSON.
---
Original Encoding:\n{text}

JSONDecodeError:\n{error}

Fixed Encoding:\n"""
    return call_default_llm(prompt)


# TODO move this to promptedgraph
