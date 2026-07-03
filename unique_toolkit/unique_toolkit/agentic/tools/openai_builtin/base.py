from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Generic, TypeVar

from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit.agentic.tools.schemas import ToolPrompts
from unique_toolkit.agentic.tools.tool import ConfigType, Tool


class OpenAIBuiltInToolName(StrEnum):
    CODE_INTERPRETER = "code_interpreter"


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

    def is_capability(self) -> bool:
        """Return True if this tool is a capability that must remain in the
        active tool set regardless of ``tool_choices`` filtering.
        Default: False.
        """
        return False


BuiltinTool = TypeVar("BuiltinTool", bound=OpenAIBuiltInTool[Any])


class ActivatorTool(Generic[ConfigType, BuiltinTool], Tool[ConfigType], ABC):
    """A regular function tool that lazily provisions a built-in tool.

    The activator is offered to the model as a cheap function tool. When the
    model calls it, ``run`` provisions the underlying built-in tool; from then
    on ``is_activated`` is True and ``get_activated_tool`` returns the built
    tool. The tool manager uses this contract to swap the activator for the
    real built-in tool once activation has happened, without knowing about any
    specific built-in.
    """

    @property
    @abstractmethod
    def is_activated(self) -> bool:
        """Whether the underlying built-in tool has been provisioned yet."""
        raise NotImplementedError()

    @abstractmethod
    def get_activated_tool(self) -> BuiltinTool:
        raise NotImplementedError()
