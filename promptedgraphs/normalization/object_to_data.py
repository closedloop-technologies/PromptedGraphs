import asyncio
import json
import tempfile
from logging import getLogger
from pathlib import Path
from string import Template
from typing import Any

import datamodel_code_generator as dcg
from pydantic import BaseModel, EmailStr, Field, RootModel

from promptedgraphs import __version__ as version
from promptedgraphs.code_execution.safer_python_exec import safer_exec
from promptedgraphs.generation.schema_from_model import schema_from_model
from promptedgraphs.llms.chat import Chat

logger = getLogger(__name__)

SYSTEM_MESSAGE = """
We are a data entry system tasked with properly formatting data based on a provided schema.  You will be given data that does not conform to the required schema and you are tasked with lightly editing the object to conform with the provided schema.

If it is a 'value_error' only return the corrected value.
If the corrected value is an object, return it in json format otherwise return just the value with no explanation.
"""

MESSAGE_TEMPLATE = Template(
    """
# Validation Error: $error_type
$error_msg

## Required schema
```
$schema
```

## Object
```
$obj
```
"""
)


async def correct_value_error(
    obj: dict, schema: dict, error_type: str, error_msg: str
) -> Any:
    """Corrects a value error in a data object."""
    obj_str = json.dumps(obj, indent=4)
    msg = MESSAGE_TEMPLATE.substitute(
        obj=obj_str,
        schema=json.dumps(schema, indent=4),
        error_type=error_type,
        error_msg=error_msg,
    ).strip()
    chat = Chat()

    # TODO replace with a tiktoken model and pad the message by 2x
    max_tokens = len(obj_str)

    response = await chat.chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE.strip()},
            {"role": "system", "content": msg},
        ],
        **{
            "max_tokens": min(4_096, max_tokens),
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        },
    )
    return json.loads(response.choices[0].message.content)


def get_sub_object(data_object: dict, loc: list[str]) -> dict:
    """Gets a sub-object from a data object."""

    for key in loc:
        data_object = data_object[key]

    sub_obj = {key: data_object}
    if len(loc) > 1:
        for key in loc[-2::-1]:
            sub_obj = {key: sub_obj}
    return sub_obj


def get_subschema(schema_spec: dict, loc: list[str]) -> dict:
    """Gets a sub-schema from a schema specification."""
    # TODO handle array items
    for key in loc:
        if "properties" in schema_spec:
            schema_spec = schema_spec["properties"][key]
        else:
            schema_spec = schema_spec[key]
    return schema_spec


def set_data_object_value(
    data_object: dict, new_value: Any, old_value: Any, loc: list[str]
):
    """Sets a value in a data object."""
    for key in loc[:-1]:
        data_object = data_object[key]
    if loc[-1] in new_value:
        data_object[loc[-1]] = new_value[loc[-1]]
    else:
        data_object[loc[-1]] = new_value


def data_model_to_schema(data_model: list[BaseModel] | BaseModel) -> dict:
    """Converts a Pydantic model to a JSON schema."""
    if isinstance(data_model, list) or str(data_model).startswith("list["):
        x = data_model.__args__[0]
        return RootModel[list[x]].model_json_schema()
    return data_model.model_json_schema()


def schema_to_data_model(schema_spec: dict) -> tuple[BaseModel, str]:
    """Converts a JSON schema to a Pydantic model.
    WARNING: This function uses the output of the datamodel-codegen and schema_spec
    and runs `exec` to execute the result. This is a potential security risk and should be used with caution.

    Returns the compiled datamodel and the generated code as a string.
    """
    input_text = json.dumps(schema_spec, indent=4)

    output_file = Path(tempfile.mkstemp(prefix="promptedgraphs_")[1])

    # Get the class name from the schema specification
    class_name = schema_spec.get("title", "DataModel")

    dcg.generate(
        input_=input_text,
        class_name=class_name,
        target_python_version=dcg.PythonVersion.PY_310,
        output=output_file,
        custom_file_header=f"# PromptedGraphs {version}\n# generated by datamodel-codegen",
    )
    model_code = Path(output_file).read_text()
    output_file.unlink()  # Delete the temporary file

    # Get the constucted object from the model code in the exec environment
    exec_variable_scope = safer_exec(model_code)
    return exec_variable_scope, model_code, class_name


async def update_data_object(
    data_object: dict, schema_spec: dict, errors: list[str] = None
):
    """Updates the data object with error information."""
    logger.debug(f"Updating data object with error: {errors}")
    corrections = []
    for error in errors():
        # if error["type"] not in {"value_error", "string_type"}:
        #     raise ValueError(f"Error type not supported: {error['type']}")
        old_value = get_sub_object(data_object, loc=error["loc"])
        new_value = await correct_value_error(
            old_value,
            get_subschema(schema_spec, loc=error["loc"]),
            error_type=error["type"],
            error_msg=error["msg"],
        )
        set_data_object_value(
            data_object,
            new_value=new_value,
            old_value=old_value,
            loc=error["loc"],
        )
        corrections.append(
            (error["loc"], error["type"], error["msg"], old_value, new_value)
        )
    return data_object, corrections


async def object_to_data(
    data_object: dict | list,
    schema_spec: dict | None = None,
    data_model: BaseModel | None = None,
    coerce: bool = True,
    retry_count: int = 10,
) -> BaseModel | list[BaseModel]:
    """Converts data to fit a given schema, applying light reformatting like type casting and field renaming.

    Args:
        data_object (Union[dict, list]): The data to reformat.
        schema_spec (Optional[Dict], optional): The schema specification for reformatting. Defaults to None.
        data_model (Optional[BaseModel], optional): The Pydantic model for reformatting. Defaults to None.
        coerce (bool, optional): Whether to coerce data types. Defaults to True.

    Returns:
        Union[dict, list]: The reformatted data.
    """
    if isinstance(data_object, list):
        return [
            await object_to_data(obj, schema_spec, data_model, coerce)
            for obj in data_object
        ]
    if schema_spec and not data_model:
        data_models, model_code, class_name = schema_to_data_model(schema_spec)
        # TODO load all of the data_models into local scope
        data_model = data_models[class_name]
    if not coerce:
        return data_model(**data_object)

    # Ensure schema_spec is defined. This is needed for the update_data_object function.
    schema_spec = schema_spec or schema_from_model(data_model)

    corrections = []
    while retry_count > 0:
        try:
            if len(corrections):
                logger.info(f"Coercing data with {len(corrections)}corrections")
                for c in corrections:
                    logger.info(
                        f"Correcting {c[0]} with {c[1]}: {c[2]} - {c[3]} -> {c[4]}"
                    )
            return data_model(**data_object)
        except Exception as e:
            data_object, new_corrections = await update_data_object(
                data_object, schema_spec, errors=e.errors
            )
            if new_corrections:
                corrections.extend(new_corrections)
        retry_count -= 1

    raise ValueError("Failed to coerce data to schema.")


async def example():
    data = {
        "name": "John Doe",
        "age": "10",
        "email": "john.doe@gmail",
    }

    class UserBioData(BaseModel):
        name: str
        age: int = Field(..., gt=0)
        email: EmailStr

    schema = schema_from_model(UserBioData)
    print(schema)

    data_model = await object_to_data(data, schema)
    print(data_model)


if __name__ == "__main__":
    asyncio.run(example())
