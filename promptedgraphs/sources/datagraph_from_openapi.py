import asyncio
import contextlib
import datetime
import json
import logging
import os
import re
import tempfile
from pathlib import Path

import requests
import tqdm
import yaml
from datamodel_code_generator import __main__ as datamodel_code_generator_cli
from dotenv import load_dotenv

from promptedgraphs.config import load_config
from promptedgraphs.llms.helpers import _sync_wrapper, extract_code_blocks
from promptedgraphs.models import ChatMessage

load_dotenv()
load_config()

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE_API_TO_SCHEMAS = """You are a python developer tasked with building pydantic data models to enforce types for various API calls.
Below is a subset of an OpenAPI spec for the endpoint `{endpoint}` with some already generated pydantic data models.

Convert the openAPI json spec into pydantic data models.  Use pydantic.Field to keep types, title and description information.

Make sure to enclose the pydantic data models within a code block like:
```python
from typing import Dict, List
from pydantic import BaseModel, Field


class ExampleRequest(BaseModel):
    pass


class ExampleResponse(BaseModel):
    pass


class SomeEntity(BaseModel):
    pass
```
Where possible use the already generated pydantic data models, avoid creating model with no properties.

The response should only contain one python code block.  Your job depends on this.  Take a breath you got this!
"""


def load_api_specification(api_specification_path):
    """
    Loads the API specification from a file.
    """
    if (api_specification_path is None) or (api_specification_path == ""):
        raise ValueError(
            "api_specification_path cannot be None or empty."
            "Please provide a valid path to the API specification."
        )
    # check if its a web address
    if api_specification_path.startswith("http"):
        api_specification = requests.get(api_specification_path)
        if api_specification.status_code != 200:
            raise ValueError(
                "api_specification_path is not a valid path to the API specification."
            )
        api_specification = api_specification.text

        if api_specification_path.endswith(".yaml"):
            # Remove non-printable characters
            api_specification = re.sub(
                r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", api_specification
            )
            # Now you can safely load the YAML
            spec = yaml.safe_load(api_specification)
        else:
            try:
                spec = json.loads(api_specification)
            except json.decoder.JSONDecodeError as e:
                raise ValueError(
                    "api_specification_path is not a valid path to the API specification."
                ) from e
    else:
        if api_specification_path.endswith(".yaml"):
            with open(api_specification_path) as f:
                spec = yaml.safe_load(f)
        else:
            with open(api_specification_path) as f:
                spec = json.load(f)
    return spec


def process_paths(spec: dict):
    """spec is a dict created from yaml.safe_load or json.loads and follows the OpenAPI specification."""
    print(spec)


async def build_schemas(
    endpoint: str,
    api_spec_json: str,
    example_models: str = None,
    external_references: dict[str, str] = None,
) -> tuple[dict]:
    """Convert function signatures into OpenAPI specs and pydantic datamodels"""

    external_references = external_references or {}

    messages = [
        ChatMessage(
            role="system",
            content=SYSTEM_MESSAGE_API_TO_SCHEMAS.format(endpoint=endpoint),
        )
    ]
    messages.append(ChatMessage(role="user", content=api_spec_json))
    if example_models:
        messages.append(
            ChatMessage(
                role="assistant",
                content=f"Already Generated Pydantic Models\n\n{example_models}",
            )
        )
    messages.extend(
        ChatMessage(
            role="assistant",
            content=f"Additional documentation loaded from {url}\n\n{html}",
        )
        for url, html in external_references.items()
    )
    data = await _sync_wrapper(
        messages, model="gpt-3.5-turbo-16k-0613", max_tokens=16_000
    )

    # pull out the json and pydantic code blocks
    content = data.get("choices")[0]["message"]["content"]
    results = extract_code_blocks(content)
    missing_types = {"python"} - {r["block_type"] for r in results}
    if len(missing_types):  # Try again
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
        data = await _sync_wrapper(
            messages, model="gpt-3.5-turbo-16k-0613", max_tokens=16_000
        )
        content = data.get("choices")[0]["message"]["content"]
        results.extend(extract_code_blocks(content))

    # Append the function signature documentation to the python code block
    docs = f"""# {endpoint}\n\n```python\n{api_spec_json}\n\n```"""
    for url, html in external_references.items():
        docs += f"\n\n## Additional documentation loaded from {url}\n\n{html}"
    results.append({"block_type": "md", "content": docs})

    return results


async def register_api_as_datasource(
    api_specification_path: str,
    name: str = None,
    datasource_registry: str = None,
):
    if api_specification_path.startswith("http"):
        name = name or api_specification_path.split("/")[-1].split(".")[0]
    else:
        name = name or api_specification_path.split(os.sep)[-1].split(".")[0]
    assert name, "You must provide a name for the datasource"

    datasource_registry = Path(datasource_registry or "./data_models/")
    output_dir = datasource_registry / name
    output_dir.mkdir(exist_ok=True, parents=True)

    spec = load_api_specification(api_specification_path)

    # Deep copy
    partial_spec = json.loads(json.dumps(spec))
    partial_spec.pop("paths", None)

    pbar = tqdm.tqdm(
        total=1 + len(spec.get("paths", {})), desc="Generating DataModels from API"
    )
    pbar.set_description(f"Generating DataModels from Spec: {name}")
    spec_datamodels = generate_datamodels_from_spec(spec)
    pbar.update(1)

    tasks = []
    output_fnames = []
    for path, path_spec in spec.get("paths", {}).items():
        for method, method_spec in path_spec.items():
            endpoint = f"{method.upper()} {path}"
            pbar.set_description(f"Generating DataModels for: {endpoint}")
            partial_spec["paths"] = {path: method_spec}

            out_fname = re.sub(r"[ /{}]+", "_", endpoint.lower())
            out_fname = output_dir / (re.sub(r"_+", "_", out_fname).strip("_"))
            output_fnames.append(out_fname)
            schemas = await build_schemas(
                endpoint,
                json.dumps(partial_spec, indent=2),
                example_models=spec_datamodels,
            )
            tasks.append(schemas)

            for schema in schemas:
                suffix = (
                    "py" if schema["block_type"] == "python" else schema["block_type"]
                )
                with open(f"{out_fname}.{suffix}", "w") as f:
                    f.write(schema["content"])

                for schema in schemas:
                    suffix = (
                        "py"
                        if schema["block_type"] == "python"
                        else schema["block_type"]
                    )
                    with open(f"{out_fname}.{suffix}", "w") as f:
                        f.write(schema["content"])

        pbar.update(1)

    meta = {
        "name": name,
        "api_specification_path": api_specification_path,
        "description": json.dumps(spec.get("info", {})),
        "as_of": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    }
    with open(output_dir / "meta.jsonl", "a") as f:
        f.write(json.dumps(meta) + "\n")


def generate_datamodels_from_spec(spec: dict):
    _, fname = tempfile.mkstemp(prefix="global-", suffix=".yaml")
    _, output_models = tempfile.mkstemp(prefix="global-", suffix=".py")

    with open(fname, "w") as f:
        f.write(yaml.safe_dump(spec))

    datamodel_code_generator_cli.main(
        [
            f'--input="{fname}"',
            "--target-python-version=3.10",
            f"--output={output_models}",
        ]
    )

    with open(output_models) as f:
        spec_datamodels = f.read()

    with contextlib.suppress(Exception):
        os.remove(fname)
        os.remove(output_models)
    return spec_datamodels

    # Aggregate all the schemas into one file


if __name__ == "__main__":
    load_dotenv()

    ogtags_spec = "https://api.ogtags.dev/openapi.json"

    viator = "data_models/viator/viator-openapi.json"
    asyncio.run(register_api_as_datasource(viator, name="viator"))

    # https://developer.sabre.com/product-catalog?f%5B0%5D=product_type%3Aapi_reference
    xs = []
    for x in xs:
        asyncio.run(
            register_api_as_datasource(
                x, name="sabre-" + x.split("/")[-1].split(".")[0]
            )
        )
