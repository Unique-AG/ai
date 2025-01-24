import json
import math
from enum import StrEnum
from typing import Any, Optional, Self
from uuid import uuid4

from humps import camelize
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    field_validator,
    model_serializer,
    model_validator,
)

from unique_toolkit.language_model.utils import format_message

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
    TOOL = "tool"


class LanguageModelFunction(BaseModel):
    model_config = model_config

    id: Optional[str] = None
    name: str
    arguments: Optional[dict[str, Any] | str] = None  # type: ignore

    @field_validator("arguments", mode="before")
    def set_arguments(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

    @field_validator("id", mode="before")
    def randomize_id(cls, value):
        return uuid4().hex

    @model_serializer()
    def serialize_model(self):
        seralization = {}
        if self.id:
            seralization["id"] = self.id
        seralization["name"] = self.name
        if self.arguments:
            seralization["arguments"] = json.dumps(self.arguments)
        return seralization


class LanguageModelFunctionCall(BaseModel):
    model_config = model_config

    id: Optional[str] = None
    type: Optional[str] = None
    function: LanguageModelFunction

    @staticmethod
    def create_assistant_message_from_tool_calls(
        tool_calls: list[LanguageModelFunction],
    ):
        assistant_message = LanguageModelAssistantMessage(
            content="",
            tool_calls=[
                LanguageModelFunctionCall(
                    id=tool_call.id,
                    type="function",
                    function=tool_call,
                )
                for tool_call in tool_calls
            ],
        )
        return assistant_message


class LanguageModelMessage(BaseModel):
    model_config = model_config
    role: LanguageModelMessageRole
    content: str | list[dict] | None = None
    tool_calls: list[LanguageModelFunctionCall] | None = None

    def __str__(self):
        if not self.content:
            message = ""
        if isinstance(self.content, str):
            message = self.content
        elif isinstance(self.content, list):
            message = json.dumps(self.content)

        return format_message(self.role.capitalize(), message=message, num_tabs=1)


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
    parsed: dict | None = None
    refusal: str | None = None

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.ASSISTANT


class LanguageModelToolMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.TOOL
    name: str
    tool_call_id: str

    def __str__(self):
        return format_message(
            user=self.role.capitalize(),
            message=f"{self.name}, {self.tool_call_id}, {self.content}",
            num_tabs=1,
        )

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.TOOL


class LanguageModelMessages(RootModel):
    root: list[
        LanguageModelMessage
        | LanguageModelToolMessage
        | LanguageModelAssistantMessage
        | LanguageModelSystemMessage
        | LanguageModelUserMessage
    ]

    def __str__(self):
        return "\n\n".join([str(message) for message in self.root])

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

    fraction_input: float = Field(default=0.4, le=1, ge=0)

    @model_validator(mode="after")
    def check_required_fields(self):
        # Best case input and output is determined
        if self.token_limit_input and self.token_limit_output:
            self.token_limit = self.token_limit_input + self.token_limit_output
            self.fraction_input = self.token_limit_input / self.token_limit
            return self

        # Deal with case where only token_limit and optional fraction_input is given
        if self.token_limit:
            if not self.fraction_input:
                self.fraction_input = 0.4

            self.token_limit_input = math.floor(self.fraction_input * self.token_limit)
            self.token_limit_output = math.floor(
                (1 - self.fraction_input) * self.token_limit
            )
            return self

        raise ValueError(
            'Either "token_limit_input" and "token_limit_output" must be provided together, or "token_limit" must be provided.'
        )


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
    name: str = Field(
        ...,
        pattern=r"^[a-zA-Z1-9_-]+$",
        description="Name must adhere to the pattern ^[a-zA-Z_-]+$",
    )
    description: str
    parameters: LanguageModelToolParameters
    returns: LanguageModelToolParameterProperty | LanguageModelToolParameters | None = (
        None
    )
