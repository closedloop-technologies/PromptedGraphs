"""Loads the configuration file for the QuantReady package."""
# Load the configuration file
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from promptedgraphs import __description__ as description
from promptedgraphs import __title__ as name
from promptedgraphs import __version__ as version


@dataclass
class Config:
    """Configuration class for PromptedGraphs"""

    name: str = name
    description: str = description
    version: str = version
    openai_api_key: str | None = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    ogtags_api_key: str | None = field(
        default_factory=lambda: os.getenv("OGTAGS_API_KEY")
    )

    def __repr__(self):
        # Mask the value of openai_api_key
        secret_keys = {"openai_api_key", "ogtags_api_key"}

        # Create a dictionary of all attributes to display
        attributes = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }
        for key in secret_keys:
            value = getattr(self, key)
            attributes[key] = None if value is None else re.sub(r".", "*", value)
        # Generate string representation of the object
        attribute_strings = [
            f"{key}={value}" for key, value in attributes.items() if value is not None
        ]
        return f"Config({', '.join(attribute_strings)})"


def load_config() -> Config:
    load_dotenv(
        verbose=True,
        dotenv_path=Path(__file__).parent.joinpath(".env"),
        override=False,
    )
    return Config(
        name=name,
        description=description,
        version=version,
    )
