from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit.content import ContentChunk

from unique_swot.services.collection.registry import ContentChunkRegistry

# ============================================================================
# Extraction Models - Used for initial extraction from source data
# ============================================================================


class WeaknessItem(BaseModel):
    """Individual weakness identified during extraction phase."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        description="Concise title capturing the essence of the weakness"
    )
    justification: str = Field(
        description="Comprehensive context and analysis explaining why this is a weakness, including disadvantages and challenges"
    )
    reference_chunk_ids: list[str] = Field(
        description="Chunk IDs that support this weakness (format: [chunk_x][chunk_y])"
    )


class WeaknessesExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """
    Extraction phase output: Raw weaknesses identified from source documents.
    This is used during the initial extraction from batches of source data.
    """

    model_config = ConfigDict(extra="forbid")

    weaknesses: list[WeaknessItem] = Field(
        description="List of weaknesses extracted from the sources"
    )

    @classmethod
    def group_batches(
        cls, batches: Sequence["WeaknessesExtraction"]
    ) -> "WeaknessesExtraction":
        """Combine multiple extraction batches by concatenating all weaknesses."""
        all_weaknesses = []
        for batch in batches:
            all_weaknesses.extend(batch.weaknesses)
        return cls(weaknesses=all_weaknesses)


# ============================================================================
# Report/Summary Models - Used for final aggregated output
# ============================================================================


class WeaknessCategory(BaseModel):
    """
    A thematic grouping of related weaknesses for better organization.
    Examples: Resource Constraints, Operational Inefficiencies, Market Position
    """

    model_config = ConfigDict(extra="forbid")

    category_name: str = Field(
        description="Name of the weakness category (e.g., 'Resource Limitations', 'Process Inefficiencies', 'Capability Gaps')"
    )
    summary: str = Field(
        description="Brief overview of this category and why these weaknesses are challenging. Include chunk references [chunk_x][chunk_y]."
    )
    weaknesses: list[WeaknessItem] = Field(
        description="Deduplicated and refined weaknesses belonging to this category"
    )


class WeaknessesReport(BaseModel):
    """
    Final consolidated report after summarization phase.
    Contains deduplicated, categorized, and constructively organized weaknesses.
    """

    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(
        description="High-level strategic overview of key weaknesses and their impact on performance. Include chunk references [chunk_x][chunk_y]."
    )
    categories: list[WeaknessCategory] = Field(
        description="Weaknesses organized by thematic categories for clarity and strategic insight"
    )
    improvement_priorities: list[str] = Field(
        description="Priority areas for improvement and remediation based on identified weaknesses",
    )

    @classmethod
    def create_from_failed(cls):
        return cls(
            executive_summary="Not available", categories=[], improvement_priorities=[]
        )

    def get_referenced_chunks(
        self, chunk_registry: ContentChunkRegistry
    ) -> list[ContentChunk]:
        chunks = []
        for category in self.categories:
            for weakness in category.weaknesses:
                for chunk_id in weakness.reference_chunk_ids:
                    chunk = chunk_registry.retrieve(chunk_id)
                    if chunk is not None:
                        chunks.append(chunk)
        return chunks
