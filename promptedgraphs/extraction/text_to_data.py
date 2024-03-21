from pydantic import BaseModel


def text_to_data(text: str, model: BaseModel) -> dict:
    """Extracts structured data from unstructured text into an instance of a DataModel.

    Args:
        text (str): The unstructured text to extract data from.
        model (BaseModel): The Pydantic BaseModel to structure the extracted data into.

    Returns:
        dict: The extracted data structured according to the DataModel.
    """
