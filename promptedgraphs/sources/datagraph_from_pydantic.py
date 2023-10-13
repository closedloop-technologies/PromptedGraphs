import asyncio
import logging
import re
import traceback
from pathlib import Path
from typing import Any

import black
import isort
import tqdm
from pydantic import BaseModel, Field

from promptedgraphs.llms.coding import fix_code

logger = logging.getLogger(__name__)

# Restrictive environment
allowed_globals = {
    "__import__": __import__,
    "BaseModel": BaseModel,
    "Field": Field,
    "bytes": bytes,
}


def kindofsafe_exec(code, dependencies: dict = None):
    variables = {}
    dependencies = dependencies or allowed_globals

    for snippet in code.split(
        "\n\n"
    ):  # Loading in code by chunks helps with dependency resolution
        dependencies.update(variables)
        exec(snippet, dependencies, variables)
    return variables


def is_pydantic_base_model(cls: Any) -> bool:
    return isinstance(cls, type) and issubclass(cls, BaseModel)


def extract_fields_and_type(cls: type[BaseModel]) -> list[tuple[str, type, str]]:
    results = []
    if type(cls) == type(BaseModel):
        return []
    schema = cls.model_json_schema()
    properties = schema.get("properties", {})
    for field_name, field_info in properties.items():
        if field_info["type"] == "array":
            results.append((field_name, cls, "item"))
        else:
            results.append((field_name, cls, "object"))
    return results


def process_file(file_path):
    with open(file_path) as file:
        file_content = file.read()

    # Things can throw weird errors if multiple definitions of the same name are in the same file

    local_vars = kindofsafe_exec(file_content)
    for name, cls in local_vars.items():
        if issubclass(cls, BaseModel) and hasattr(cls, "model_json_schema"):
            cls.model_json_schema()

            # TODO  GO HAM ON THIS


def aggregate_python_files(fdir):
    fdir = Path(fdir)
    code = []

    for fname in fdir.glob("*.py"):
        with open(fname) as f:
            c = black.format_str(f.read(), mode=black.FileMode())
            code.append(c)
            try:
                black.format_str("\n\n".join(code), mode=black.FileMode())
            except Exception:
                logger.error(f"Static code error in: {fname}")
                return

    # move all imports to the top
    code = move_imports_to_top("\n\n".join(code))
    config = isort.Config(profile="black")
    code = isort.code(code, config=config)

    # reformat one more time
    code = black.format_str(code, mode=black.FileMode())

    with open(fdir / "_all.py", "w") as f:
        f.write(code)

    return fdir / "_all.py"


def move_imports_to_top(code):
    lines = code.split("\n")

    # Separating import lines and other lines
    import_lines = [
        line for line in lines if re.match(r"^(import |from .+ import)", line)
    ]
    other_lines = [
        line for line in lines if not re.match(r"^(import |from .+ import)", line)
    ]

    # Combining the lines and writing back to the file
    return "\n".join(import_lines + other_lines)


async def validate_python_files(fdir):
    fnames = sorted(fdir.glob("*.py"))
    for fname in tqdm.tqdm(fnames):
        if fname.name == "_all.py":
            continue
        code = Path(fname).read_text()

        history = []
        i = 0
        while i < 4:
            code = black.format_str(code, mode=black.FileMode())
            kindofsafe_exec(code)
            # break
            try:
                code = black.format_str(code, mode=black.FileMode())
                kindofsafe_exec(code)
                break
            except Exception as e:
                i += 1
                if i >= 4:
                    logger.error(f"Code error in: {fname}")
                    return

                logger.warning(f"fixing code error in: {fname} - take {i} - {e}")
                code, history = await fix_code(
                    code, error=e, tb=traceback.format_exc(), history=history
                )
        if i > 0:
            logger.warning(f"Fixed code error in: {fname}")
            with open(fname, "w") as f:
                f.write(code)


async def python_files_pipeline(fdir):
    await validate_python_files(fdir)
    file_path = aggregate_python_files(fdir)
    results = process_file(file_path)
    print(results)
    return results


if __name__ == "__main__":
    fdir = Path("data_models/googlemaps.client.Client")
    asyncio.run(python_files_pipeline(fdir))

    # for r in results:
