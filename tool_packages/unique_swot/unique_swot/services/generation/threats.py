from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from unique_swot.services.generation.base import (
    ReportGenerationOutputModel,
    ReportGenerationSummaryModel,
)

# ============================================================================
# Extraction Models - Used for initial extraction from source data
# ============================================================================


class ThreatItem(BaseModel):
    """Individual threat identified during extraction phase."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Concise title capturing the essence of the threat")
    justification: str = Field(
        description="Comprehensive context and analysis explaining why this is a threat, including potential risks and impact"
    )
    reference_chunk_ids: list[str] = Field(
        description="Chunk IDs that support this threat (format: [chunk_x][chunk_y])"
    )


class ThreatsAnalysis(ReportGenerationOutputModel["ThreatsAnalysis"]):
    """
    Extraction phase output: Raw threats identified from source documents.
    This is used during the initial extraction from batches of source data.
    """

    model_config = ConfigDict(extra="forbid")

    threats: list[ThreatItem] = Field(
        description="List of threats extracted from the sources"
    )

    @classmethod
    def group_batches(cls, batches: Sequence["ThreatsAnalysis"]) -> "ThreatsAnalysis":
        """Combine multiple extraction batches by concatenating all threats."""
        all_threats = []
        for batch in batches:
            all_threats.extend(batch.threats)
        return cls(threats=all_threats)


# ============================================================================
# Report/Summary Models - Used for final aggregated output
# ============================================================================


class ThreatCategory(BaseModel):
    """
    A thematic grouping of related threats for better organization.
    Examples: Competitive Pressures, Regulatory Risks, Market Challenges
    """

    model_config = ConfigDict(extra="forbid")

    category_name: str = Field(
        description="Name of the threat category (e.g., 'Competitive Threats', 'Regulatory Risks', 'Economic Challenges')"
    )
    summary: str = Field(
        description="Brief overview of this category and why these threats are concerning. Include chunk references [chunk_x][chunk_y]."
    )
    threats: list[ThreatItem] = Field(
        description="Deduplicated and refined threats belonging to this category"
    )


class ThreatsReport(ReportGenerationSummaryModel["ThreatsReport"]):
    """
    Final consolidated report after summarization phase.
    Contains deduplicated, categorized, and strategically organized threats.
    """

    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(
        description="High-level strategic overview of key threats and their potential impact. Include chunk references [chunk_x][chunk_y]."
    )
    categories: list[ThreatCategory] = Field(
        description="Threats organized by thematic categories for clarity and strategic insight"
    )
    mitigation_strategies: list[str] = Field(
        description="Suggested strategies to mitigate or respond to identified threats",
    )

    
    @classmethod
    def create_from_failed(cls):
        return cls(
            executive_summary="Not available",
            categories=[],
            mitigation_strategies=[]
        )