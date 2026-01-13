from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Generic, TypeVar

from openai.types.responses.response_create_params import (
    ToolChoiceTypesParam,  # pyright: ignore[reportPrivateImportUsage]
)
from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit.agentic.tools.schemas import ToolPrompts


class OpenAIBuiltInToolName(StrEnum):
    CODE_INTERPRETER = "AzureCodeInterpreter"

    @classmethod
    def to_forced_tool(cls, tool_name: str) -> ToolChoiceTypesParam:
        match tool_name:
            case OpenAIBuiltInToolName.CODE_INTERPRETER:
                return {"type": "code_interpreter"}
            case _:
                raise ValueError(f"Unknown tool name: {tool_name}")


BuiltInToolType = CodeInterpreter  # Add other tool types when needed
ToolType = TypeVar("ToolType", bound=BuiltInToolType)


class OpenAIBuiltInTool(ABC, Generic[ToolType]):
    @property
    @abstractmethod
    def name(self) -> OpenAIBuiltInToolName:
        raise NotImplementedError()

    @abstractmethod
    def tool_description(self) -> BuiltInToolType:
        raise NotImplementedError()

    @abstractmethod
    def get_tool_prompts(self) -> ToolPrompts:
        raise NotImplementedError()

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def is_exclusive(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def takes_control(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError()
