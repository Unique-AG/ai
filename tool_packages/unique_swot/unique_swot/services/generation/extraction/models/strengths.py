from typing import Sequence

from pydantic import Field

from unique_swot.utils import (
    StructuredOutputResult,
    StructuredOutputWithNotification,
)

# ============================================================================
# Extraction Models - Used for initial extraction from source data
# ============================================================================


class StrengthItem(StructuredOutputResult):
    """Individual strength identified during extraction phase."""

    justification: str = Field(
        description="Comprehensive context and analysis explaining why this is a strength, including competitive advantages and benefits"
    )
    title: str = Field(
        description="Concise title capturing the essence of the strength"
    )
    reference_chunk_ids: list[str] = Field(
        description="Chunk IDs that support this strength (format: [chunk_x][chunk_y])"
    )


class StrengthsExtraction(StructuredOutputWithNotification):
    """
    Extraction phase output: Raw strengths identified from source documents.
    This is used during the initial extraction from batches of source data.
    """

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
        notification_message = ""
        progress_notification_message = ""
        if len(batches):
            notification_message = batches[-1].notification_message
            progress_notification_message = batches[-1].progress_notification_message
        return cls(
            strengths=all_strengths,
            notification_message=notification_message,
            progress_notification_message=progress_notification_message,
        )

    @property
    def number_of_items(self) -> int:
        return len(self.strengths)

    def get_items(self) -> list[StrengthItem]:
        """Get the list of extracted strength items."""
        return self.strengths
