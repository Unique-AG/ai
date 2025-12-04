from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.reporting.prompts.config import (
    ReportingPromptConfig,
)


def get_swot_reporting_system_prompt(
    component: SWOTComponent, reporting_prompt_config: ReportingPromptConfig
) -> str:
    if component == SWOTComponent.STRENGTHS:
        return reporting_prompt_config.strengths
    elif component == SWOTComponent.WEAKNESSES:
        return reporting_prompt_config.weaknesses
    elif component == SWOTComponent.OPPORTUNITIES:
        return reporting_prompt_config.opportunities
    elif component == SWOTComponent.THREATS:
        return reporting_prompt_config.threats
    else:
        raise ValueError(f"Invalid component: {component}")


__all__ = [
    "get_swot_reporting_system_prompt",
]
