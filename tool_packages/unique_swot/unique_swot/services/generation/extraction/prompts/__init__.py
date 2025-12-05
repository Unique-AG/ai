from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.extraction.prompts.config import (
    ExtractionPromptConfig,
)


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
