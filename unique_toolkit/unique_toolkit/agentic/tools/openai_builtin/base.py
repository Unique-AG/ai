from abc import ABC, abstractmethod
from enum import StrEnum

from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit.agentic.tools.schemas import ToolPrompts


class OpenAIBuiltInToolName(StrEnum):
    CODE_INTERPRETER = "code_interpreter"


BuiltInToolType = CodeInterpreter  # Add other tool types when needed


class OpenAIBuiltInTool[ToolType: BuiltInToolType](ABC):
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
