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

SWOTExtractionModel = (
    StrengthsExtraction
    | WeaknessesExtraction
    | OpportunitiesExtraction
    | ThreatsExtraction
)

__all__ = [
    "SWOTExtractionModel",
]
