from typing import Self, Sequence

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit.content import ContentChunk

from unique_swot.services.collection.registry import ContentChunkRegistry

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


# ============================================================================
# Report/Summary Models - Used for final aggregated output
# ============================================================================


class OpportunityCategory(BaseModel):
    """
    A thematic grouping of related opportunities for better organization.
    Examples: Market Expansion, Technological Innovation, Strategic Partnerships
    """

    model_config = ConfigDict(extra="forbid")

    category_name: str = Field(
        description="Name of the opportunity category (e.g., 'Market Expansion Opportunities', 'Emerging Technologies')"
    )
    summary: str = Field(
        description="Brief overview of this category and why these opportunities matter. Include chunk references [chunk_x][chunk_y]."
    )
    opportunities: list[OpportunityItem] = Field(
        description="Deduplicated and refined opportunities belonging to this category"
    )


class OpportunitiesReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    """
    Final consolidated report after summarization phase.
    Contains deduplicated, categorized, and strategically organized opportunities.
    """

    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(
        description="High-level strategic overview of key opportunities and their implications. Include chunk references [chunk_x][chunk_y]."
    )
    categories: list[OpportunityCategory] = Field(
        description="Opportunities organized by thematic categories for clarity and strategic insight"
    )
    key_recommendations: list[str] = Field(
        description="Actionable strategic recommendations for capitalizing on identified opportunities",
    )

    @classmethod
    def create_from_failed(cls):
        return cls(
            executive_summary="Not available", categories=[], key_recommendations=[]
        )

    def get_referenced_chunks(
        self, chunk_registry: ContentChunkRegistry
    ) -> list[ContentChunk]:
        chunks = []
        for category in self.categories:
            for opportunity in category.opportunities:
                for chunk_id in opportunity.reference_chunk_ids:
                    chunk = chunk_registry.retrieve(chunk_id)
                    if chunk is not None:
                        chunks.append(chunk)
        return chunks
