"""The purpose of this class is to extract data from text
and return it as a structured object or a list of structured objects.

Base case:
 * Provide text and specify the return type as a Pydantic model and it returns an instance of that model

"""

from promptedgraphs.helpers import camelcase_to_words, format_fieldinfo
from promptedgraphs.models import ChatMessage

SYSTEM_MESSAGE = """
You are a Qualitative User Researcher and Linguist. Your task is to extract structured data from text to be passed into python's `{name}(BaseModel)` pydantic class.
Maintain as much verbatim text as possible, light edits are allowed, feel free to remove any text that is not relevant to the label.
If there is not information applicable for a particular field, use the value `==NA==`.

In particular look for the following fields: {label_list}.

{label_definitions}
"""
