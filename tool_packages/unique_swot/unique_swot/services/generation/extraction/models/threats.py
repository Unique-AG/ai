from typing import Sequence

from pydantic import Field

from unique_swot.utils import (
    StructuredOutputResult,
    StructuredOutputWithNotification,
)

# ============================================================================
# Extraction Models - Used for initial extraction from source data
# ============================================================================


class ThreatItem(StructuredOutputResult):
    """Individual threat identified during extraction phase."""

    justification: str = Field(
        description="Comprehensive context and analysis explaining why this is a threat, including potential risks and impact"
    )
    title: str = Field(description="Concise title capturing the essence of the threat")
    reference_chunk_ids: list[str] = Field(
        description="Chunk IDs that support this threat (format: [chunk_x][chunk_y])"
    )


class ThreatsExtraction(StructuredOutputWithNotification):
    """
    Extraction phase output: Raw threats identified from source documents.
    This is used during the initial extraction from batches of source data.
    """

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
        notification_message = ""
        progress_notification_message = ""
        if len(batches):
            notification_message = batches[-1].notification_message
            progress_notification_message = batches[-1].progress_notification_message
        return cls(
            threats=all_threats,
            notification_message=notification_message,
            progress_notification_message=progress_notification_message,
        )

    @property
    def number_of_items(self) -> int:
        return len(self.threats)

    def get_items(self) -> list[ThreatItem]:
        """Get the list of extracted threat items."""
        return self.threats
