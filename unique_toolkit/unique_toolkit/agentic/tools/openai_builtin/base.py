from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Generic, TypeVar

from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit.agentic.tools.tool import HasPromptsProtocol, HasSettingsProtocol


class OpenAIBuiltInToolName(StrEnum):
    CODE_INTERPRETER = "code_interpreter"


BuiltInToolType = CodeInterpreter  # Add other tool types when needed
ToolType = TypeVar("ToolType", bound=BuiltInToolType)


class OpenAIBuiltInTool(
    HasPromptsProtocol, HasSettingsProtocol, ABC, Generic[ToolType]
):
    name: str

    @abstractmethod
    def tool_description(self) -> BuiltInToolType:
        raise NotImplementedError()
