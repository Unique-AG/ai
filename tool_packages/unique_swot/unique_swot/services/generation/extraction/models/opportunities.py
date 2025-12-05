from typing import Self, Sequence

from pydantic import Field

from unique_swot.utils import (
    StructuredOutputResult,
    StructuredOutputWithNotification,
)

# ============================================================================
# Extraction Models - Used for initial extraction from source data
# ============================================================================


class OpportunityItem(StructuredOutputResult):
    justification: str = Field(
        description="A comprehensive context and analysis of the opportunity, explaining why it is significant."
    )
    title: str = Field(description="The title of the opportunity")
    reference_chunk_ids: list[str] = Field(
        description="The chunk IDs of the references that support the opportunity"
    )


class OpportunitiesExtraction(StructuredOutputWithNotification):
    """
    Extraction phase output: Raw opportunities identified from source documents.
    This is used during the initial extraction from batches of source data.
    """

    opportunities: list[OpportunityItem] = Field(
        description="The opportunities identified in the analysis"
    )

    @classmethod
    def group_batches(cls, batches: Sequence[Self]) -> Self:
        """Combine multiple OpportunitiesAnalysis batches into a single analysis."""
        all_opportunities: list[OpportunityItem] = []
        for batch in batches:
            all_opportunities.extend(batch.opportunities)

        notification_message = ""
        progress_notification_message = ""
        if len(batches):
            notification_message = batches[-1].notification_message
            progress_notification_message = batches[-1].progress_notification_message

        return cls(
            opportunities=all_opportunities,
            notification_message=notification_message,
            progress_notification_message=progress_notification_message,
        )

    @property
    def number_of_items(self) -> int:
        return len(self.opportunities)

    def get_items(self) -> list[OpportunityItem]:
        """Get the list of extracted opportunity items."""
        return self.opportunities
