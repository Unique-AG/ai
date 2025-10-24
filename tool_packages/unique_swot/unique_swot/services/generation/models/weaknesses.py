from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

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

    @property
    def number_of_items(self) -> int:
        return len(self.weaknesses)
