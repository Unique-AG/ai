from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit import LanguageModelName
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

from unique_swot.services.generation.config import ReportGenerationConfig
from unique_swot.services.generation.extraction.config import ExtractionConfig
from unique_swot.services.report import ReportRendererConfig
from unique_swot.services.source_management.config import SourceManagementConfig

TOOL_DESCRIPTION = """
This tool is used to perfom a SWOT analysis of a company by analyzing its strengths, weaknesses, opportunities, and threats.
The user can either generate a new SWOT analysis or modify an existing one.
If the user simply says RUN, the tool will generate a new SWOT analysis.

If the user simply says RUN, It means that he expects the tool to generate a new SWOT analysis.
"""


class SwotAnalysisToolConfig(BaseToolConfig):
    cache_scope_id: str = Field(
        default="",
        description="The scope id for the SWOT analysis cache.",
    )
    language_model: LMI = Field(
        default=get_LMI_default_field(LanguageModelName.AZURE_GPT_5_2025_0807),
        description="The language model to use for the SWOT analysis.",
    )
    source_management_config: SourceManagementConfig = Field(
        default_factory=SourceManagementConfig,
        description="The configuration for the source management.",
    )
    extraction_config: ExtractionConfig = Field(
        default_factory=ExtractionConfig,
        description="The configuration for the extraction.",
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
