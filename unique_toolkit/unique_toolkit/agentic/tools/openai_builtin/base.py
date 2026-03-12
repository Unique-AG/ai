from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Generic, TypeVar

from openai.types.responses.tool_param import CodeInterpreter

try:
    from openai.types.responses.tool_param import FunctionShellToolParam
except ImportError:
    FunctionShellToolParam = dict[str, Any]  # type: ignore[assignment, misc]

from unique_toolkit.agentic.tools.schemas import ToolPrompts


class OpenAIBuiltInToolName(StrEnum):
    CODE_INTERPRETER = "code_interpreter"
    HOSTED_SHELL = "hosted_shell"


# Maps internal tool names to the type value expected by the OpenAI Responses API
# in tool_choice. e.g. HOSTED_SHELL is "hosted_shell" internally but the API
# expects {"type": "shell"}.
BUILTIN_TOOL_API_TYPE: dict[str, str] = {
    "code_interpreter": "code_interpreter",
    "hosted_shell": "shell",
}


BuiltInToolType = CodeInterpreter | FunctionShellToolParam
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
