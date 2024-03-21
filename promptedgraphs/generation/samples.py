from pydantic import BaseModel


def samples(model: BaseModel) -> list[dict]:
    """Generates sample data for a given DataModel.

    Args:
        model (BaseModel): The Pydantic BaseModel instance to generate samples for.

    Returns:
        List[dict]: A list of dictionaries, each representing a sample data point.
    """
