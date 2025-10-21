from unique_swot.services.generation.models.opportunities import (
    OpportunitiesExtraction,
    OpportunitiesReport,
)
from unique_swot.services.generation.models.strengths import (
    StrengthsExtraction,
    StrengthsReport,
)
from unique_swot.services.generation.models.threats import (
    ThreatsExtraction,
    ThreatsReport,
)
from unique_swot.services.generation.models.weaknesses import (
    WeaknessesExtraction,
    WeaknessesReport,
)

SWOTExtractionModel = (
    StrengthsExtraction
    | WeaknessesExtraction
    | OpportunitiesExtraction
    | ThreatsExtraction
)

SWOTAnalysisReportModel = (
    StrengthsReport | WeaknessesReport | OpportunitiesReport | ThreatsReport
)

__all__ = [
    "SWOTExtractionModel",
    "SWOTAnalysisReportModel",
]
