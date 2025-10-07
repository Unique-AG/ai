from pydantic import Field
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

from unique_swot.services.generation import ReportGenerationConfig


class SwotConfig(BaseToolConfig):
    report_generation_config: ReportGenerationConfig = Field(
        default_factory=ReportGenerationConfig,
        description="The configuration for the report generation.",
    )
    tool_description: str = Field(
        default="The SWOT analysis tool.",
        description="The description of the SWOT analysis tool.",
    )
    tool_description_for_system_prompt: str = Field(
        default="The system prompt for the SWOT analysis tool.",
        description="The system prompt for the SWOT analysis tool.",
    )
    tool_format_information_for_system_prompt: str = Field(
        default="The format information for the SWOT analysis tool.",
        description="The format information for the SWOT analysis tool.",
    )
    tool_description_for_user_prompt: str = Field(
        default="The user prompt for the SWOT analysis tool.",
        description="The user prompt for the SWOT analysis tool.",
    )
    tool_format_information_for_user_prompt: str = Field(
        default="The format information for the SWOT analysis tool.",
        description="The format information for the SWOT analysis tool.",
    )
    tool_format_reminder_for_user_prompt: str = Field(
        default="The format reminder for the SWOT analysis tool.",
        description="The format reminder for the SWOT analysis tool.",
    )