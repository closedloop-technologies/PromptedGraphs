"""Bootstrap a datagraph from APIs and functions"""
import asyncio
import datetime
import inspect
import json
import logging
import os
import re
from pathlib import Path

import googlemaps
import tqdm
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from promptedgraphs.config import load_config
from promptedgraphs.llms.helpers import _sync_wrapper, extract_code_blocks
from promptedgraphs.llms.openai_streaming import streaming_chat_completion_request
from promptedgraphs.models import ChatMessage
from promptedgraphs.sources.rtfm import fetch_from_ogtags

load_dotenv()
load_config()

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE_FN_TO_SCHEMAS = """You are a python developer tasked with building pydantic data models to enforce types for various function calls.
Below is a function's call signature and doc string with optionally additional documentation

# Steps:
1.  Write the function as an openAPI spec in JSON assuming the endpoint is GET `/{fn_name}`.  Make sure to enclose the JSON data in a code block

2. Then convert the openAPI json spec above into pydantic data models.  Use pydantic.Field to keep types, title and description information.

Make sure to enclose the pydantic data models within a code block like
```python
from typing import Dict, List
from pydantic import BaseModel, Field


class ExampleRequest(BaseModel):
    pass


class ExampleResponse(BaseModel):
    pass
```

The response should only contain two code blocks (one with JSON data and one with python code)
"""


def get_functions_from_object(fn: classmethod):
    """Get functions from an object"""
    return [
        getattr(fn, a)
        for a in dir(fn)
        if callable(getattr(fn, a)) and not a.startswith("_")
    ]


def build_function_signature(fn: classmethod):
    """Build a function from a signature"""
    sig = inspect.signature(fn)
    doc = (fn.__doc__ or "").strip()
    return f'def {fn.__name__}{str(sig)}:\n    """{doc}' + '\n    """\n    ....'


def extract_urls_with_anchors(text):
    if not text:
        return []
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+(?:#[a-zA-Z0-9-_]*)?"
    )
    return sorted(set(url_pattern.findall(text)))


def slim_down_html(html: str, anchor: str = None) -> tuple[str, bool]:
    html = BeautifulSoup(html, features="html.parser")
    # remove all script and style and visual elements
    for script in html(["script", "style", "svg", "img"]):
        script.extract()

    if anchor:
        if anchor := html.find(id=anchor):
            return str(anchor), True

    if article := html.find("article"):
        return str(article), False
    elif main := html.find("main"):
        return str(main), False
    elif body := html.find("body"):
        return str(body), False
    return str(html), False


async def html_to_markdown(html, url=None):
    """Convert html to markdown"""
    if url and "#" in url:
        anchor = url.split("#")[1] if url else None
    else:
        anchor = None
    html, used_anchor = slim_down_html(html, anchor=anchor)
    if anchor and not used_anchor:
        url = url.split("#")[0]

    SYSTEM_MESSAGE = """Format webpage as markdown"""
    payload = ""
    async for event in streaming_chat_completion_request(
        messages=[
            ChatMessage(
                role="system",
                content=SYSTEM_MESSAGE,
            ),
            ChatMessage(role="user", content=html),
        ],
        functions=None,
        config=load_config(),
        stream=False,
    ):
        if event.data:
            payload += event.data
        elif event.retry:
            print(f"Retry: {event.retry}")

    data = json.loads(payload)
    return data["choices"][0]["message"]["content"], url


async def build_function_schemas(
    fn_name: str, fn_signature: str, external_references: dict[str, str] = None
) -> tuple[dict]:
    """Convert function signatures into OpenAPI specs and pydantic datamodels"""

    external_references = external_references or {}

    messages = [
        ChatMessage(
            role="system",
            content=SYSTEM_MESSAGE_FN_TO_SCHEMAS.format(fn_name=fn_name),
        )
    ]
    messages.append(ChatMessage(role="user", content=fn_signature))
    messages.extend(
        ChatMessage(
            role="assistant",
            content=f"Additional documentation loaded from {url}\n\n{html}",
        )
        for url, html in external_references.items()
    )
    data = await _sync_wrapper(messages)

    # pull out the json and pydantic code blocks
    content = data.get("choices")[0]["message"]["content"]
    results = extract_code_blocks(content)
    if len(results) != 2:  # Try again
        missing_types = {"json", "python"} - {r["block_type"] for r in results}
        logger.warning(f"Missing code blocks of type: {missing_types}")
        messages.append(
            ChatMessage(
                role="assistant",
                content=content,
            )
        )
        messages.append(
            ChatMessage(
                role="user",
                content=f"Please provide the missing `{','.join(missing_types)}` code block",
            ),
        )
        data = await _sync_wrapper(messages)
        content = data.get("choices")[0]["message"]["content"]
        results.extend(extract_code_blocks(content))

    # Append the function signature documenation to the python code block
    docs = f"""# {fn_name}\n\n```python\n{fn_signature}\n\n```"""
    for url, html in external_references.items():
        docs += f"\n\n## Additional documentation loaded from {url}\n\n{html}"
    results.append({"block_type": "md", "content": docs})

    return results


async def register_function_as_datasource(
    obj: object,
    name: str = None,
    datasource_registry: str = None,
):
    name = (
        name or getattr(obj, "__name__", None) or str(obj).split()[0].replace("<", "")
    )
    assert name, "You must provide a name for the datasource"

    datasource_registry = Path(datasource_registry or "./data_models/")
    output_dir = datasource_registry / name
    output_dir.mkdir(exist_ok=True, parents=True)

    meta = {
        "name": name,
        "description": obj.__doc__ or "",
        "as_of": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    }

    fns = get_functions_from_object(obj)
    ittr = tqdm.tqdm(fns, desc=f"Building schemas for {name}")
    for fn in ittr:
        ittr.set_description(f"Building schema for {name}::{fn.__name__}")
        links = extract_urls_with_anchors(fn.__doc__)
        sig = build_function_signature(fn)

        external_references = {}
        for link in tqdm.tqdm(links, desc="Fetching external references"):
            if link in external_references:
                continue
            if html := fetch_from_ogtags(link):
                html, new_link = await html_to_markdown(html, url=link)
                external_references[new_link] = html

        fn_schemas = await build_function_schemas(
            fn.__name__, sig, external_references=external_references
        )

        for fn_schema in fn_schemas:
            suffix = (
                "py" if fn_schema["block_type"] == "python" else fn_schema["block_type"]
            )
            with open(output_dir / f"{fn.__name__}.{suffix}", "w") as f:
                f.write(fn_schema["content"])

    with open(datasource_registry / "meta.jsonl", "a") as f:
        f.write(json.dumps(meta) + "\n")

    # Aggregate all the schemas into one file


if __name__ == "__main__":
    load_dotenv()
    gmaps = googlemaps.Client(key=os.environ["GOOGLEMAPS_API_KEY"])
    asyncio.run(register_function_as_datasource(gmaps))
