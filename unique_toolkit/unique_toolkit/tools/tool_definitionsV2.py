from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Generic, List, Self, TypeVar
from unique_toolkit.language_model import LanguageModelToolDescription
from typing_extensions import deprecated
# import baseModel from pedantic
from unique_toolkit.language_model import LanguageModelFunction
from pydantic import BaseModel, Field, model_validator, root_validator

from unique_toolkit.unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.unique_toolkit.tools.tool_definitions import BaseToolConfig, Tool, ToolCallResponse, ToolSettings
from unique_toolkit.unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter


class BaseToolConfigV2(BaseToolConfig):
    class ToolCallConfig(BaseModel):
        description: str = Field(
            default="Base",  
            description="The tool description must be set by subclasses",
        )

        parameters: type[BaseModel] = Field(
            default=BaseModel,
            description="The tool parameters configuration must be set by subclasses",
        )

    class PromptsConfig(BaseModel):
        description_for_system_prompt: str = Field(
            default="",
            description="The description of the tool for the system prompt. ",
        )
        format_information_for_system_prompt: str = Field(
            default="",
            description="The format information for the system prompt.",
        )
        format_reminder_for_user_prompt: str = Field(
            default="",
            description="A short reminder for the user prompt for formatting rules for the tool.",
        )
        result_handling_instructions: str = Field(
            default="",
            description="Instructions for the LLM on how to handle the result of the tool call.",
        )
        example_use_cases: List[str] = Field(
            default=[],
            description="Example use cases for the tool, to help the LLM understand how to use it.",
        )

    tool_call: ToolCallConfig = Field(
        default_factory=ToolCallConfig,
        description="Configuration for the tool, including description and parameters",
    )

    prompts: PromptsConfig = Field(
        default_factory=PromptsConfig,
        description="Configuration for prompts related to the tool",
    )

    # This makes sure that the settings are all present in all subclasses and that they define a default value. 
    @model_validator(mode="after")
    def validate_tool_description(cls):
        if cls.__class__ is BaseToolConfig:
            return cls  # Skip validation for the base class
        if cls.tool_call.description == "Base":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'tool_description'."
            )
        if cls.tool_call.parameters == BaseModel:
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'tool_parameters_config'."
            )
        if cls.prompts.description_for_system_prompt == "":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'description_for_system'."
            )
        if cls.prompts.format_information_for_system_prompt == "":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'format_information_for_system_prompt'."
            )
        if cls.prompts.format_reminder_for_user_prompt == "":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'format_reminder_for_user_prompt'."
            )
        if cls.prompts.result_handling_instructions == "":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'result_handling_instructions'."
            )
        if not cls.prompts.example_use_cases:
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'example_use_cases'."
            )
        return cls
    

ConfigTypeV2 = TypeVar("ConfigTypeV2", bound=BaseToolConfigV2)



class ToolV2(Tool[ConfigTypeV2]):
    name: str

    def tool_description(self) -> LanguageModelToolDescription:
         return LanguageModelToolDescription(
            name=self.name,
            description=self.settings.configuration.tool_call.description,
            parameters=self.settings.configuration.tool_call.parameters,
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.settings.configuration.prompts.description_for_system_prompt

    
    def tool_format_information_for_system_prompt(self) -> str:
        return self.settings.configuration.prompts.format_information_for_system_prompt

    def tool_format_reminder_for_user_prompt(self) -> str:
        """A short reminder for the user prompt for formatting rules for the tool.
        You can use this if the LLM fails to follow the formatting rules.
        """
        return self.settings.configuration.prompts.format_reminder_for_user_prompt
    
    def result_handling_instructions(self) -> str:
        """Instructions for the LLM on how to handle the result of the tool call.
        This is used to ensure that the LLM understands how to process the tool's output.
        """
        return self.settings.configuration.prompts.result_handling_instructions

    def example_use_cases(self) -> List[str]:
        """Example use cases for the tool, to help the LLM understand how to use it."""
        return self.settings.configuration.prompts.example_use_cases



    @abstractmethod
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        raise NotImplementedError

   
  
    def __init__(
        self,
        settings: ToolSettings[ConfigTypeV2],
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter
    ):
        self.settings = settings
        self.tool_progress_reporter = tool_progress_reporter
        self.event = event


