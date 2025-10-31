from unique_swot.services.generation.config import ReportGenerationConfig
from unique_swot.services.generation.contexts import (
    ReportGenerationContext,
    ReportModificationContext,
    ReportSummarizationContext,
    SWOTComponent,
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
    ExtractionPromptConfig,
    SummarizationPromptConfig,
)
from unique_swot.services.generation.utils import batch_parser


def get_swot_extraction_system_prompt(
    component: SWOTComponent, extraction_prompt_config: ExtractionPromptConfig
) -> str:
    if component == SWOTComponent.STRENGTHS:
        return extraction_prompt_config.strengths
    elif component == SWOTComponent.WEAKNESSES:
        return extraction_prompt_config.weaknesses
    elif component == SWOTComponent.OPPORTUNITIES:
        return extraction_prompt_config.opportunities
    elif component == SWOTComponent.THREATS:
        return extraction_prompt_config.threats
    else:
        raise ValueError(f"Invalid component: {component}")


def get_swot_summarization_system_prompt(
    component: SWOTComponent, summarization_prompt_config: SummarizationPromptConfig
) -> str:
    if component == SWOTComponent.STRENGTHS:
        return summarization_prompt_config.strengths
    elif component == SWOTComponent.WEAKNESSES:
        return summarization_prompt_config.weaknesses
    elif component == SWOTComponent.OPPORTUNITIES:
        return summarization_prompt_config.opportunities
    elif component == SWOTComponent.THREATS:
        return summarization_prompt_config.threats
    else:
        raise ValueError(f"Invalid component: {component}")


def get_swot_extraction_model(
    component: SWOTComponent,
) -> type[SWOTExtractionModel]:
    if component == SWOTComponent.STRENGTHS:
        return StrengthsExtraction
    elif component == SWOTComponent.WEAKNESSES:
        return WeaknessesExtraction
    elif component == SWOTComponent.OPPORTUNITIES:
        return OpportunitiesExtraction
    elif component == SWOTComponent.THREATS:
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
