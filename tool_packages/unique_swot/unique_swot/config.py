from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

from unique_swot.services.generation import ReportGenerationConfig
from unique_swot.services.report import ReportRendererConfig

TOOL_DESCRIPTION = """
The SWOT analysis tool. This tool is used to analyze the strengths, weaknesses, opportunities, and threats of a company.\n
The user can either generate a new SWOT analysis or modify an existing one.\n
If the user simply says RUN, the tool will generate a new SWOT analysis.

If the user simply says RUN, It means that he expects the tool to generate a new SWOT analysis.
"""


class SwotAnalysisToolConfig(BaseToolConfig):
    cache_scope_id: str = Field(
        default="",
        description="The scope id for the SWOT analysis cache.",
    )
    report_generation_config: ReportGenerationConfig = Field(
        default_factory=ReportGenerationConfig,
        description="The configuration for the report generation.",
    )
    report_renderer_config: ReportRendererConfig = Field(
        default_factory=ReportRendererConfig,
        description="The configuration for the report renderer.",
    )
    tool_description: str = Field(
        default=TOOL_DESCRIPTION,
        description="The description of the SWOT analysis tool.",
    )
    tool_description_for_system_prompt: str = Field(
        default=TOOL_DESCRIPTION,
        description="The system prompt for the SWOT analysis tool.",
    )
    tool_format_information_for_system_prompt: SkipJsonSchema[str] = Field(
        default="",
        description="The format information for the SWOT analysis tool.",
    )
    tool_description_for_user_prompt: SkipJsonSchema[str] = Field(
        default="",
        description="The user prompt for the SWOT analysis tool.",
    )
    tool_format_information_for_user_prompt: SkipJsonSchema[str] = Field(
        default="",
        description="The format information for the SWOT analysis tool.",
    )
    tool_format_reminder_for_user_prompt: SkipJsonSchema[str] = Field(
        default="",
        description="The format reminder for the SWOT analysis tool.",
    )
