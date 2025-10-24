from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

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


class ThreatsExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """
    Extraction phase output: Raw threats identified from source documents.
    This is used during the initial extraction from batches of source data.
    """

    model_config = ConfigDict(extra="forbid")

    threats: list[ThreatItem] = Field(
        description="List of threats extracted from the sources"
    )

    @classmethod
    def group_batches(
        cls, batches: Sequence["ThreatsExtraction"]
    ) -> "ThreatsExtraction":
        """Combine multiple extraction batches by concatenating all threats."""
        all_threats = []
        for batch in batches:
            all_threats.extend(batch.threats)
        return cls(threats=all_threats)

    @property
    def number_of_items(self) -> int:
        return len(self.threats)
