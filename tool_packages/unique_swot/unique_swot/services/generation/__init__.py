from enum import StrEnum

from unique_swot.services.generation.config import ReportGenerationConfig
from unique_swot.services.generation.contexts import (
    ReportGenerationContext,
    ReportModificationContext,
    ReportSummarizationContext,
)
from unique_swot.services.generation.generator import (
    extract_swot_from_sources,
    modify_report,
    summarize_swot_extraction,
)
from unique_swot.services.generation.models import SWOTExtractionModel
from unique_swot.services.generation.models.opportunities import (
    OpportunitiesExtraction,
)
from unique_swot.services.generation.models.strengths import (
    StrengthsExtraction,
)
from unique_swot.services.generation.models.threats import (
    ThreatsExtraction,
)
from unique_swot.services.generation.models.weaknesses import (
    WeaknessesExtraction,
)
from unique_swot.services.generation.prompts import (
    OPPORTUNITIES_EXTRACTION_TEMPLATE,
    OPPORTUNITIES_SUMMARIZATION_TEMPLATE,
    STRENGTHS_EXTRACTION_TEMPLATE,
    STRENGTHS_SUMMARIZATION_TEMPLATE,
    THREATS_EXTRACTION_TEMPLATE,
    THREATS_SUMMARIZATION_TEMPLATE,
    WEAKNESSES_EXTRACTION_TEMPLATE,
    WEAKNESSES_SUMMARIZATION_TEMPLATE,
)
from unique_swot.services.generation.utils import batch_parser


class SWOTComponent(StrEnum):
    STRENGTHS = "strengths"
    WEAKNESSES = "weaknesses"
    OPPORTUNITIES = "opportunities"
    THREATS = "threats"


def get_swot_extraction_system_prompt(component: SWOTComponent) -> str:
    if component == SWOTComponent.STRENGTHS:
        return STRENGTHS_EXTRACTION_TEMPLATE
    elif component == SWOTComponent.WEAKNESSES:
        return WEAKNESSES_EXTRACTION_TEMPLATE
    elif component == SWOTComponent.OPPORTUNITIES:
        return OPPORTUNITIES_EXTRACTION_TEMPLATE
    elif component == SWOTComponent.THREATS:
        return THREATS_EXTRACTION_TEMPLATE
    else:
        raise ValueError(f"Invalid component: {component}")


def get_swot_summarization_system_prompt(component: SWOTComponent) -> str:
    if component == SWOTComponent.STRENGTHS:
        return STRENGTHS_SUMMARIZATION_TEMPLATE
    elif component == SWOTComponent.WEAKNESSES:
        return WEAKNESSES_SUMMARIZATION_TEMPLATE
    elif component == SWOTComponent.OPPORTUNITIES:
        return OPPORTUNITIES_SUMMARIZATION_TEMPLATE
    elif component == SWOTComponent.THREATS:
        return THREATS_SUMMARIZATION_TEMPLATE
    else:
        raise ValueError(f"Invalid component: {component}")


def get_swot_extraction_model(
    component: SWOTComponent,
) -> type[SWOTExtractionModel]:
    if component == "strengths":
        return StrengthsExtraction
    elif component == "weaknesses":
        return WeaknessesExtraction
    elif component == "opportunities":
        return OpportunitiesExtraction
    elif component == "threats":
        return ThreatsExtraction
    else:
        raise ValueError(f"Invalid component: {component}")


# Export all the important components
__all__ = [
    "SWOTComponent",
    "get_swot_extraction_system_prompt",
    "get_swot_summarization_system_prompt",
    "get_swot_extraction_model",
    "extract_swot_from_sources",
    "ReportSummarizationContext",
    "ReportGenerationConfig",
    "ReportGenerationContext",
    "ReportModificationContext",
    "modify_report",
    "summarize_swot_extraction",
    "batch_parser",
]
