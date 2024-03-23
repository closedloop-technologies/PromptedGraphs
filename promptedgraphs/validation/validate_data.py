from pydantic import BaseModel

from promptedgraphs.normalization.data_to_schema import data_to_schema


def validate_data(
    data_object: dict,
    schema_spec: dict | None = None,
    data_model: BaseModel | None = None,
) -> bool:
    """Validates a data object against a schema specification or a Pydantic DataModel.

    Args:
        data_object (dict): The data object to validate.
        schema_spec (Optional[dict], optional): The schema specification to validate against. Defaults to None.
        data_model (Optional[BaseModel], optional): The Pydantic BaseModel to validate against. Defaults to None.

    Returns:
        bool: True if the data object is valid, False otherwise.
    """
    try:
        data_to_schema(
            data_object=data_object,
            schema_spec=schema_spec,
            data_model=data_model,
            coerce=False,
        )
        return True
    except ValueError:
        return False
