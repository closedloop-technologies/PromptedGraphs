from pydantic import BaseModel


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
