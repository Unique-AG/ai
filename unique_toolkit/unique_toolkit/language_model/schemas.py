from enum import StrEnum
from typing import Optional

from humps import camelize
from pydantic import BaseModel, ConfigDict, RootModel, field_validator

# set config to convert camelCase to snake_case
model_config = ConfigDict(alias_generator=camelize, populate_by_name=True, arbitrary_types_allowed=True)


class LanguageModelMessageRole(StrEnum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class LanguageModelFunction(BaseModel):
    model_config = model_config

    name: str
    arguments: dict[str, any]


class LanguageModelFunctionCall(BaseModel):
    model_config = model_config

    id: str
    type: str
    function: LanguageModelFunction


class LanguageModelMessage(BaseModel):
    model_config = model_config

    role: LanguageModelMessageRole
    content: str
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


class LanguageModelResponseMessage(BaseModel):
    content: str


class LanguageModelName(StrEnum):
    AZURE_GPT_35_TURBO_0613 = "AZURE_GPT_35_TURBO_0613"
    AZURE_GPT_35_TURBO = "AZURE_GPT_35_TURBO"
    AZURE_GPT_35_TURBO_16K = "AZURE_GPT_35_TURBO_16K"
    AZURE_GPT_4_0613 = "AZURE_GPT_4_0613"
    AZURE_GPT_4_TURBO_1106 = "AZURE_GPT_4_TURBO_1106"
    AZURE_GPT_4_VISION_PREVIEW = "AZURE_GPT_4_VISION_PREVIEW"
    AZURE_GPT_4_32K_0613 = "AZURE_GPT_4_32K_0613"
    AZURE_GPT_4_TURBO_2024_0409 = "AZURE_GPT_4_TURBO_2024_0409"
    AZURE_GPT_4o_2024_0513 = "AZURE_GPT_4o_2024_0513"

