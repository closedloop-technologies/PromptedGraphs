from dataclasses import dataclass
from typing import Any

from dataclasses_json import dataclass_json
from pydantic import BaseModel


@dataclass_json
@dataclass
class EntityLabel:
    label: str
    name: str
    description: str | None


@dataclass_json
@dataclass
class EntityReference:
    start: int
    end: int
    label: str
    text: str | None = None
    reason: str | None = None


@dataclass_json
@dataclass
class TextwithEntities:
    text: str
    ents: list[EntityReference]


class ChatMessage(BaseModel):
    role: str
    content: str
    name: str | None = None


class FunctionParameter(BaseModel):
    type: str
    description: str | None


class FunctionArrayParameter(BaseModel):
    type: str
    description: str | None
    items: Any | None


class FunctionParameters(BaseModel):
    type: str
    properties: dict[str, FunctionParameter]
    required: list[str]


class ChatFunction(BaseModel):
    name: str
    description: str
    dependencies: list[str] | None
    parameters: FunctionParameters
