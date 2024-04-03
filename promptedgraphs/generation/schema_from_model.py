from pydantic import BaseModel, RootModel


def schema_from_model(data_model: list[BaseModel] | BaseModel) -> dict:
    """Generates a schema from a Pydantic DataModel.

    Args:
        model (BaseModel): The Pydantic BaseModel instance to generate a schema for.

    Returns:
        dict: The generated schema as a dictionary.
    """
    if isinstance(data_model, list) or str(data_model).startswith("list["):
        x = data_model.__args__[0]
        return RootModel[list[x]].model_json_schema()
    return data_model.model_json_schema()
