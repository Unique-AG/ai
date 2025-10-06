import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field


class OpenAIModels(StrEnum):
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"
    GPT_4O_2024_08_06_MINI = "gpt-4o-2024-08-06-mini"


class AnthropicModels(StrEnum):
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet"
    CLAUDE_3_5_SONNET_2024_06_20 = "claude-3-5-sonnet-2024-06-20"


class UniqueModels(StrEnum):
    UNIQUE_1 = "unique-1"
    UNIQUE_2 = "unique-2"


class BaseEngins(BaseModel):
    id: str
    name: str = Field(default="base")
    description: str
    model: Annotated[
        str,
        BeforeValidator(
            lambda v: v.value,
            json_schema_input_type=OpenAIModels | AnthropicModels | UniqueModels,
        ),
    ]


class OpenAIEngine(BaseEngins):
    type: Literal["openai"]
    api_key: str
    name: str = Field(default="openai")
    model: Annotated[OpenAIModels, BeforeValidator(lambda v: v.value)]


class AnthropicEngine(BaseEngins):
    type: Literal["anthropic"]
    api_key: str
    name: str = Field(default="anthropic")
    model: Annotated[AnthropicModels, BeforeValidator(lambda v: v.value)]


class UniqueEngine(BaseEngins):
    type: Literal["unique"]
    api_key: str
    name: str = Field(default="unique")
    model: Annotated[UniqueModels, BeforeValidator(lambda v: v.value)]


class Config(BaseModel):
    engine: OpenAIEngine | UniqueEngine


file = Path(__file__).parent / "test.json"

file.open("w").write(json.dumps(Config.model_json_schema()))
