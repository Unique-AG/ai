from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.reporting.models.opportunities import (
    ConsolidatedOpportunitiesReport,
)
from unique_swot.services.generation.reporting.models.strengths import (
    ConsolidatedStrengthsReport,
)
from unique_swot.services.generation.reporting.models.threats import (
    ConsolidatedThreatsReport,
)
from unique_swot.services.generation.reporting.models.weaknesses import (
    ConsolidatedWeaknessesReport,
)

SWOTConsolidatedReport = (
    ConsolidatedStrengthsReport
    | ConsolidatedWeaknessesReport
    | ConsolidatedOpportunitiesReport
    | ConsolidatedThreatsReport
)


def get_swot_consolidated_report_model(
    component: SWOTComponent,
) -> type[SWOTConsolidatedReport]:
    if component == SWOTComponent.STRENGTHS:
        return ConsolidatedStrengthsReport
    elif component == SWOTComponent.WEAKNESSES:
        return ConsolidatedWeaknessesReport
    elif component == SWOTComponent.OPPORTUNITIES:
        return ConsolidatedOpportunitiesReport
    elif component == SWOTComponent.THREATS:
        return ConsolidatedThreatsReport
    else:
        raise ValueError(f"Invalid component: {component}")


__all__ = [
    "SWOTConsolidatedReport",
    "get_swot_consolidated_report_model",
]
