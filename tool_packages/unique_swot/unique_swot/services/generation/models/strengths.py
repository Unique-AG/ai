from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit.content import ContentChunk

from unique_swot.services.collection.registry import ContentChunkRegistry

# ============================================================================
# Extraction Models - Used for initial extraction from source data
# ============================================================================


class StrengthItem(BaseModel):
    """Individual strength identified during extraction phase."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        description="Concise title capturing the essence of the strength"
    )
    justification: str = Field(
        description="Comprehensive context and analysis explaining why this is a strength, including competitive advantages and benefits"
    )
    reference_chunk_ids: list[str] = Field(
        description="Chunk IDs that support this strength (format: [chunk_x][chunk_y])"
    )


class StrengthsExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    """
    Extraction phase output: Raw strengths identified from source documents.
    This is used during the initial extraction from batches of source data.
    """

    model_config = ConfigDict(extra="forbid")

    strengths: list[StrengthItem] = Field(
        description="List of strengths extracted from the sources"
    )

    @classmethod
    def group_batches(
        cls, batches: Sequence["StrengthsExtraction"]
    ) -> "StrengthsExtraction":
        """Combine multiple extraction batches by concatenating all strengths."""
        all_strengths = []
        for batch in batches:
            all_strengths.extend(batch.strengths)
        return cls(strengths=all_strengths)


# ============================================================================
# Report/Summary Models - Used for final aggregated output
# ============================================================================


class StrengthCategory(BaseModel):
    """
    A thematic grouping of related strengths for better organization.
    Examples: Financial Resources, Brand & Reputation, Innovation Capabilities
    """

    model_config = ConfigDict(extra="forbid")

    category_name: str = Field(
        description="Name of the strength category (e.g., 'Financial Strength', 'Operational Excellence', 'Human Capital')"
    )
    summary: str = Field(
        description="Brief overview of this category and why these strengths are important. Include chunk references [chunk_x][chunk_y]."
    )
    strengths: list[StrengthItem] = Field(
        description="Deduplicated and refined strengths belonging to this category"
    )


class StrengthsReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    """
    Final consolidated report after summarization phase.
    Contains deduplicated, categorized, and strategically organized strengths.
    """

    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(
        description="High-level strategic overview of key strengths and their competitive advantages. Include chunk references [chunk_x][chunk_y]."
    )
    categories: list[StrengthCategory] = Field(
        description="Strengths organized by thematic categories for clarity and strategic insight"
    )
    key_insights: list[str] = Field(
        description="Key strategic insights about how strengths create competitive advantage",
    )

    @classmethod
    def create_from_failed(cls):
        return cls(executive_summary="Not available", categories=[], key_insights=[])

    def get_referenced_chunks(
        self, chunk_registry: ContentChunkRegistry
    ) -> list[ContentChunk]:
        chunks = []
        for category in self.categories:
            for strength in category.strengths:
                for chunk_id in strength.reference_chunk_ids:
                    chunk = chunk_registry.retrieve(chunk_id)
                    if chunk is not None:
                        chunks.append(chunk)
        return chunks
