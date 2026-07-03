from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from openai.types.responses import ResponseIncludable
from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit.agentic.tools.schemas import ToolPrompts

if TYPE_CHECKING:
    from unique_toolkit.agentic.tools.tool import Tool


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

    def activator(self) -> "Tool[Any] | None":
        """Return the activator function tool for a lazy built-in tool.

        If non-None, this built-in is *lazy*: the tool manager advertises the
        returned function ``Tool`` instead of the built-in spec, and the
        built-in's resources (e.g. a container) are provisioned only when the
        activator is called. A lazy built-in must be a non-exclusive
        capability tool (enforced by ``OpenAIBuiltInToolManager``).
        Default: None (eager built-in).
        """
        return None

    def get_required_include_params(self) -> list[ResponseIncludable]:
        """Return Responses API `include` values required by this tool.

        Subclasses override this when they need additional data attached to the
        response (e.g. code interpreter execution logs).  The default is an
        empty list, meaning no extra includes are needed.
        """
        return []
