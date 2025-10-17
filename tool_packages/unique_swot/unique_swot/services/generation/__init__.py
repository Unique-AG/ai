"""
SWOT Analysis Generation Services

This module provides services for generating SWOT analysis components individually
or as a complete analysis. Each component (Strengths, Weaknesses, Opportunities, Threats)
can be generated separately with specialized prompts and schemas for better precision.
"""

from enum import StrEnum

from unique_swot.services.generation.base import (
    ReportGenerationConfig,
    ReportGenerationContext,
    ReportModifyContext,
    generate_report,
    modify_report,
)
from unique_swot.services.generation.helpers import batch_parser
from unique_swot.services.generation.opportunities import (
    OPPORTUNITIES_SYSTEM_PROMPT,
    OpportunitiesAnalysis,
)
from unique_swot.services.generation.strengths import (
    STRENGTHS_SYSTEM_PROMPT,
    StrengthsAnalysis,
)
from unique_swot.services.generation.threats import (
    THREATS_SYSTEM_PROMPT,
    ThreatsAnalysis,
)
from unique_swot.services.generation.weaknesses import (
    WEAKNESSES_SYSTEM_PROMPT,
    WeaknessesAnalysis,
)


class SWOTComponent(StrEnum):
    STRENGTHS = "strengths"
    WEAKNESSES = "weaknesses"
    OPPORTUNITIES = "opportunities"
    THREATS = "threats"

SWOTAnalysisModels = (
    StrengthsAnalysis | WeaknessesAnalysis | OpportunitiesAnalysis | ThreatsAnalysis
)


def get_generation_system_prompt(component: SWOTComponent) -> str:
    if component == SWOTComponent.STRENGTHS:
        return STRENGTHS_SYSTEM_PROMPT
    elif component == SWOTComponent.WEAKNESSES:
        return WEAKNESSES_SYSTEM_PROMPT
    elif component == SWOTComponent.OPPORTUNITIES:
        return OPPORTUNITIES_SYSTEM_PROMPT
    elif component == SWOTComponent.THREATS:
        return THREATS_SYSTEM_PROMPT
    else:
        raise ValueError(f"Invalid component: {component}")


def get_analysis_model(
    component: SWOTComponent,
) -> type[
    StrengthsAnalysis | WeaknessesAnalysis | OpportunitiesAnalysis | ThreatsAnalysis
]:
    if component == "strengths":
        return StrengthsAnalysis
    elif component == "weaknesses":
        return WeaknessesAnalysis
    elif component == "opportunities":
        return OpportunitiesAnalysis
    elif component == "threats":
        return ThreatsAnalysis
    else:
        raise ValueError(f"Invalid component: {component}")


# Export all the important components
__all__ = [
    "StrengthsAnalysis",
    "WeaknessesAnalysis",
    "OpportunitiesAnalysis",
    "ThreatsAnalysis",
    "STRENGTHS_SYSTEM_PROMPT",
    "WEAKNESSES_SYSTEM_PROMPT",
    "OPPORTUNITIES_SYSTEM_PROMPT",
    "THREATS_SYSTEM_PROMPT",
    "SWOTComponent",
    "get_generation_system_prompt",
    "get_analysis_model",
    "generate_report",
    "ReportGenerationConfig",
    "ReportGenerationContext",
    "ReportModifyContext",
    "modify_report",
    "batch_parser",
]
