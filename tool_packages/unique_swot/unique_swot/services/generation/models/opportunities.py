from typing import Self, Sequence

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Extraction Models - Used for initial extraction from source data
# ============================================================================


class OpportunityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(description="The title of the opportunity")
    justification: str = Field(
        description="A comprehensive context and analysis of the opportunity, explaining why it is significant."
    )
    reference_chunk_ids: list[str] = Field(
        description="The chunk IDs of the references that support the opportunity"
    )


class OpportunitiesExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunities: list[OpportunityItem] = Field(
        description="The opportunities identified in the analysis"
    )

    @classmethod
    def group_batches(cls, batches: Sequence[Self]) -> Self:
        """Combine multiple OpportunitiesAnalysis batches into a single analysis."""
        all_opportunities = []
        for batch in batches:
            all_opportunities.extend(batch.opportunities)
        return cls(opportunities=all_opportunities)

    @property
    def number_of_items(self) -> int:
        return len(self.opportunities)
