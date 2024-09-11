import json
from enum import StrEnum
from typing import Any, Optional, Self

from humps import camelize
from pydantic import BaseModel, ConfigDict, RootModel, field_validator, model_validator

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


class LanguageModelMessageRole(StrEnum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class LanguageModelFunction(BaseModel):
    model_config = model_config

    id: Optional[str] = None
    name: str
    arguments: Optional[dict[str, list | dict | str | int | float | bool]] = None  # type: ignore

    @field_validator("arguments", mode="before")
    def set_arguments(cls, value):
        return json.loads(value)


class LanguageModelFunctionCall(BaseModel):
    model_config = model_config

    id: str
    type: Optional[str] = None
    function: LanguageModelFunction


class LanguageModelMessage(BaseModel):
    model_config = model_config

    role: LanguageModelMessageRole
    content: Optional[str | list[dict]] = None
    name: Optional[str] = None
    tool_calls: Optional[list[LanguageModelFunctionCall]] = None


class LanguageModelSystemMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.SYSTEM

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.SYSTEM


class LanguageModelUserMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.USER

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.USER


class LanguageModelAssistantMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.ASSISTANT

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.ASSISTANT


class LanguageModelMessages(RootModel):
    root: list[LanguageModelMessage]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]


class LanguageModelCompletionChoice(BaseModel):
    model_config = model_config

    index: int
    message: LanguageModelMessage
    finish_reason: str


class LanguageModelResponse(BaseModel):
    model_config = model_config

    choices: list[LanguageModelCompletionChoice]


class LanguageModelStreamResponseMessage(BaseModel):
    model_config = model_config

    id: str
    previous_message_id: str
    role: LanguageModelMessageRole
    text: str
    original_text: Optional[str] = None
    references: list[dict[str, list | dict | str | int | float | bool]] = []  # type: ignore

    # TODO make sdk return role in lowercase
    # Currently needed as sdk returns role in uppercase
    @field_validator("role", mode="before")
    def set_role(cls, value: str):
        return value.lower()


class LanguageModelStreamResponse(BaseModel):
    model_config = model_config

    message: LanguageModelStreamResponseMessage
    tool_calls: Optional[list[LanguageModelFunction]] = None


class LanguageModelTokenLimits(BaseModel):
    token_limit: Optional[int] = None
    token_limit_input: Optional[int] = None
    token_limit_output: Optional[int] = None

    @model_validator(mode="after")
    def validate_model(self):
        token_limit = self.token_limit
        token_limit_input = self.token_limit_input
        token_limit_output = self.token_limit_output

        if (
            token_limit is None
            and token_limit_input is None
            and token_limit_output is None
        ):
            raise ValueError(
                "At least one of token_limit, token_limit_input or token_limit_output must be set"
            )

        if (
            token_limit is None
            and token_limit_input is not None
            and token_limit_output is not None
        ):
            self.token_limit = token_limit_input + token_limit_output

        return self


class LanguageModelToolParameterProperty(BaseModel):
    type: str
    description: str
    enum: Optional[list[Any]] = None
    items: Optional[Self] = None


class LanguageModelToolParameters(BaseModel):
    type: str = "object"
    properties: dict[str, LanguageModelToolParameterProperty]
    required: list[str]


class LanguageModelTool(BaseModel):
    name: str
    description: str
    parameters: LanguageModelToolParameters
    returns: LanguageModelToolParameterProperty | LanguageModelToolParameters | None = (
        None
    )
