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


class ToolPrompts(BaseModel):
    system_prompt_base_instructions: str = Field(
        default="",
        description=("Helps the LLM understand how to use the tool. "
                     "This is injected into the system prompt."
                     "This might not be needed for every tool but some of the work better with user prompt "
                     "instructions while others work better with system prompt instructions."),
    )

    user_prompt_base_instructions: str = Field(
        default="",
        description=("Helps the LLM understand how to use the tool. "
                     "This is injected into the user prompt. " 
                     "This might not be needed for every tool but some of the work better with user prompt "
                     "instructions while others work better with system prompt instructions.")
    )

    system_prompt_tool_chosen_instructions: str = Field(
        default="",
        description=("Once the tool is chosen, this is injected into the system prompt"
                     " to help the LLM understand how work with the tools results."),
    )

    user_prompt_tool_chosen_instructions: str = Field(
        default="",
        description=("Once the tool is chosen, this is injected into the user prompt " 
                     "to help the LLM understand how to work with the tools results."),
    )


class Tool(ABC, Generic[ConfigType]):
    name: str

    def tool_description(self) -> LanguageModelToolDescription:
        raise NotImplementedError
    
    
    def get_prompts(self) -> ToolPrompts:
        return ToolPrompts(
            system_prompt_base_instructions="",
            user_prompt_base_instructions="",
            system_prompt_tool_chosen_instructions="",
            user_prompt_tool_chosen_instructions="",
        )


    def is_exclusive(self) -> bool:
        return self.settings.is_exclusive
    
    def is_enabled(self) -> bool:
        return self.settings.is_enabled
    
    def display_name(self) -> str:
        return self.settings.display_name
    
    def icon(self) -> str:
        return self.settings.icon
    
    def tool_selection_policy(self) -> ToolSelectionPolicy:
        return self.settings.selection_policy


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


