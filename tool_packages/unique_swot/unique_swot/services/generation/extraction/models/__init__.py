from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.extraction.models.opportunities import (
    OpportunitiesExtraction,
)
from unique_swot.services.generation.extraction.models.strengths import (
    StrengthsExtraction,
)
from unique_swot.services.generation.extraction.models.threats import (
    ThreatsExtraction,
)
from unique_swot.services.generation.extraction.models.weaknesses import (
    WeaknessesExtraction,
)

SWOTExtractionModel = (
    StrengthsExtraction
    | WeaknessesExtraction
    | OpportunitiesExtraction
    | ThreatsExtraction
)


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


__all__ = [
    "SWOTExtractionModel",
    "get_swot_extraction_model",
]
