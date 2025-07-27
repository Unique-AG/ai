from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Generic, List, Self, TypeVar
from unique_toolkit.language_model import LanguageModelToolDescription
from typing_extensions import deprecated
# import baseModel from pedantic
from unique_toolkit.language_model import LanguageModelFunction
from pydantic import BaseModel, Field, model_validator, root_validator

from unique_toolkit.unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter

class ToolSelectionPolicy(StrEnum):
    """Determine the usage policy of tools."""

    FORCED_BY_DEFAULT = "ForcedByDefault"
    ON_BY_DEFAULT = "OnByDefault"
    BY_USER = "ByUser"

class UqToolName(StrEnum):
    WEB_SEARCH = "WebSearch"
    INTERNAL_SEARCH = "InternalSearch"
    DOCUMENT_SUMMARIZER = "DocumentSummarizer"
    CHART_GENERATOR = "ChartGenerator"
    DOCUMENT_GENERATOR = "DocumentGenerator"
    DOCUMENT_PARSER = "DocumentParser"
    IMAGE_CONTENT = "ImageContent"
    TABLE_SEARCH = "TableSearch"
    BAR_CHART = "BarChart"
    LINE_CHART = "LineChart"
    PIE_CHART = "PieChart"
    BASE_TOOL = "BaseTool"


class BaseToolConfig(BaseModel):
    pass
    

ConfigType = TypeVar("ConfigType", bound=BaseToolConfig)


class ToolSettings(Generic[ConfigType]):
    configuration: ConfigType
    display_name: str
    icon: str
    selection_policy: ToolSelectionPolicy = Field(
        default=ToolSelectionPolicy.BY_USER,
    )
    is_exclusive: bool = Field(default=False)
    is_enabled: bool = Field(default=True)

    @classmethod
    def from_service_dict(cls, service_dict: dict[str, Any]) -> Self | None:
        try:
            return cls(**service_dict)
        except (ValueError, TypeError) as e:
            print(e)
            return None


class ToolCallResponse(BaseModel):
  id: str
  name: str
  debug_info: dict = {}


class Tool(ABC, Generic[ConfigType]):
    name: str

    def tool_description(self) -> LanguageModelToolDescription:
        raise NotImplementedError

    def tool_description_for_system_prompt(self) -> str:
         raise NotImplementedError

    
    def tool_format_information_for_system_prompt(self) -> str:
         raise NotImplementedError

    def tool_format_reminder_for_user_prompt(self) -> str:
        """A short reminder for the user prompt for formatting rules for the tool.
        You can use this if the LLM fails to follow the formatting rules.
        """
        raise NotImplementedError
    
    def result_handling_instructions(self) -> str:
        return ""

    def example_use_cases(self) -> List[str]:
        return []



    @abstractmethod
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        raise NotImplementedError

   
  
    def __init__(
        self,
        settings: ToolSettings[ConfigType],
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter
    ):
        self.settings = settings
        self.tool_progress_reporter = tool_progress_reporter
        self.event = event


