from pydantic import BaseModel


def data_to_schema(
    data_object: dict | list,
    schema_spec: dict | None = None,
    data_model: BaseModel | None = None,
    coerce: bool = True,
) -> dict | list:
    """Converts data to fit a given schema, applying light reformatting like type casting and field renaming.

    Args:
        data_object (Union[dict, list]): The data to reformat.
        schema_spec (Optional[Dict], optional): The schema specification for reformatting. Defaults to None.
        data_model (Optional[BaseModel], optional): The Pydantic model for reformatting. Defaults to None.
        coerce (bool, optional): Whether to coerce data types. Defaults to True.

    Returns:
        Union[dict, list]: The reformatted data.
    """
