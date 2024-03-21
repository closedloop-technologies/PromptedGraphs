from pydantic import BaseModel


def schema_from_model(model: BaseModel) -> dict:
    """Generates a schema from a Pydantic DataModel.

    Args:
        model (BaseModel): The Pydantic BaseModel instance to generate a schema for.

    Returns:
        dict: The generated schema as a dictionary.
    """
