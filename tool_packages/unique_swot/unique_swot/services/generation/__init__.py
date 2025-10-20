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
    OpportunitiesAnalysis,
    OpportunitiesReport,
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
from unique_swot.services.generation.strengths import StrengthsAnalysis, StrengthsReport
from unique_swot.services.generation.threats import ThreatsAnalysis, ThreatsReport
from unique_swot.services.generation.weaknesses import (
    WeaknessesAnalysis,
    WeaknessesReport,
)


class SWOTComponent(StrEnum):
    STRENGTHS = "strengths"
    WEAKNESSES = "weaknesses"
    OPPORTUNITIES = "opportunities"
    THREATS = "threats"


SWOTAnalysisModel = (
    StrengthsAnalysis | WeaknessesAnalysis | OpportunitiesAnalysis | ThreatsAnalysis
)

SWOTAnalysisReportModel = (
    StrengthsReport | WeaknessesReport | OpportunitiesReport | ThreatsReport
)


def get_swot_generation_system_prompt(component: SWOTComponent) -> tuple[str, str]:
    if component == SWOTComponent.STRENGTHS:
        return (STRENGTHS_EXTRACTION_TEMPLATE, STRENGTHS_SUMMARIZATION_TEMPLATE)
    elif component == SWOTComponent.WEAKNESSES:
        return WEAKNESSES_EXTRACTION_TEMPLATE, WEAKNESSES_SUMMARIZATION_TEMPLATE
    elif component == SWOTComponent.OPPORTUNITIES:
        return OPPORTUNITIES_EXTRACTION_TEMPLATE, OPPORTUNITIES_SUMMARIZATION_TEMPLATE
    elif component == SWOTComponent.THREATS:
        return THREATS_EXTRACTION_TEMPLATE, THREATS_SUMMARIZATION_TEMPLATE
    else:
        raise ValueError(f"Invalid component: {component}")


def get_analysis_models(
    component: SWOTComponent,
) -> tuple[
    type[
        StrengthsAnalysis | WeaknessesAnalysis | OpportunitiesAnalysis | ThreatsAnalysis
    ],
    type[StrengthsReport | WeaknessesReport | OpportunitiesReport | ThreatsReport],
]:
    if component == "strengths":
        return (StrengthsAnalysis, StrengthsReport)
    elif component == "weaknesses":
        return (WeaknessesAnalysis, WeaknessesReport)
    elif component == "opportunities":
        return (OpportunitiesAnalysis, OpportunitiesReport)
    elif component == "threats":
        return (ThreatsAnalysis, ThreatsReport)
    else:
        raise ValueError(f"Invalid component: {component}")


# Export all the important components
__all__ = [
    "StrengthsAnalysis",
    "WeaknessesAnalysis",
    "OpportunitiesAnalysis",
    "ThreatsAnalysis",
    "SWOTComponent",
    "get_swot_generation_system_prompt",
    "get_analysis_models",
    "generate_report",
    "ReportGenerationConfig",
    "ReportGenerationContext",
    "ReportModifyContext",
    "modify_report",
    "batch_parser",
]
