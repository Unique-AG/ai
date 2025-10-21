from pydantic import BaseModel, ConfigDict

from unique_swot.services.collection.schema import Source
from unique_swot.services.generation.models import SWOTExtractionModel


class ReportGenerationContext(BaseModel):
    """
    Context information for generating SWOT analysis reports.

    Contains all the necessary information to generate a report for a specific
    SWOT component (Strengths, Weaknesses, Opportunities, or Threats).

    Attributes:
        step_name: Name of the SWOT analysis step being executed
        system_prompt: The system prompt to guide the language model
        sources: List of data sources to analyze
        output_model: The Pydantic model class for structured output
    """

    model_config = ConfigDict(frozen=True)

    step_name: str
    extraction_system_prompt: str
    sources: list[Source]
    extraction_output_model: type[SWOTExtractionModel]


class ReportSummarizationContext(BaseModel):
    """
    Context information for summarizing SWOT analysis reports.

    Contains all the necessary information to summarize a SWOT analysis report.
    """

    model_config = ConfigDict(frozen=True)

    step_name: str
    summarization_system_prompt: str
    extraction_results: SWOTExtractionModel


class ReportModificationContext(BaseModel):
    """
    Context information for modifying existing SWOT analysis reports.

    Contains the information needed to modify an already-generated SWOT analysis
    based on new sources or specific instructions.

    Attributes:
        step_name: Name of the SWOT analysis step being modified
        system_prompt: The system prompt to guide the language model
        modify_instruction: Specific instruction for how to modify the report
        structured_report: The existing report to be modified
        sources: List of new data sources to incorporate
    """

    model_config = ConfigDict(frozen=True)

    step_name: str
    system_prompt: str
    modify_instruction: str
    structured_report: SWOTExtractionModel
    sources: list[Source]
