from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Generic, List, Self, TypeVar
from unique_toolkit.language_model import LanguageModelToolDescription
from typing_extensions import deprecated
# import baseModel from pedantic
from unique_toolkit.language_model import LanguageModelFunction
from pydantic import BaseModel, Field, model_validator, root_validator

from unique_toolkit.unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.unique_toolkit.tools.tool_definitions import BaseToolConfig, Tool, ToolCallResponse, ToolPromptInstructions, ToolSettings
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

    class PromptInstructionsConfig(BaseModel):
        system_prompt: str = Field(
        default="",
        description=("Helps the LLM understand how to use the tool. "
                     "This is injected into the system prompt."
                     "This might not be needed for every tool but some of the work better with user prompt "
                     "instructions while others work better with system prompt instructions."),
        )

        user_prompt: str = Field(
            default="",
            description=("Helps the LLM understand how to use the tool. "
                        "This is injected into the user prompt. " 
                        "This might not be needed for every tool but some of the work better with user prompt "
                        "instructions while others work better with system prompt instructions.")
        )

        system_prompt_tool_chosen: str = Field(
            default="",
            description=("Once the tool is chosen, this is injected into the system prompt"
                        " to help the LLM understand how work with the tools results."),
        )

        user_prompt_tool_chosen: str = Field(
            default="",
            description=("Once the tool is chosen, this is injected into the user prompt " 
                        "to help the LLM understand how to work with the tools results."),
        )

    tool_call: ToolCallConfig = Field(
        default_factory=ToolCallConfig,
        description="Configuration for the tool, including description and parameters",
    )

    prompts: PromptInstructionsConfig = Field(
        default_factory=PromptInstructionsConfig,
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
        if cls.prompts.system_prompt == "":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'system_prompt_base_instructions'."
            )
        if cls.prompts.user_prompt == "":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'user_prompt_base_instructions'."
            )
        if cls.prompts.system_prompt_tool_chosen == "":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'system_prompt_tool_chosen_instructions'."
            )
        if cls.prompts.user_prompt_tool_chosen == "":
            raise ValueError(
                f"Subclass {cls.__class__.__name__} must define a default value for 'user_prompt_tool_chosen_instructions'."
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

    def get_prompt_instructions(self) -> ToolPromptInstructions:
        return ToolPromptInstructions(
            system_prompt=self.settings.configuration.prompts.system_prompt,
            user_prompt=self.settings.configuration.prompts.user_prompt,
            system_prompt_tool_chosen=self.settings.configuration.prompts.system_prompt_tool_chosen,
            user_prompt_tool_chosen=self.settings.configuration.prompts.user_prompt_tool_chosen
        )


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


