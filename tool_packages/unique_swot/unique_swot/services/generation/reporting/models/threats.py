from typing import Self

from pydantic import Field

from unique_swot.utils import (
    StructuredOutputResult,
    StructuredOutputWithNotification,
)


class ThreatBulletPoint(StructuredOutputResult):
    """A single bullet point within a threat insight."""

    key_reasoning: str = Field(
        ...,
        description="Bold summary that captures the core risk in direct, evidence-based language. Should be accessible and explain the threat clearly.",
    )
    detailed_context: str = Field(
        ...,
        description="Detailed explanation with evidence and market context. Define technical terms, competitor names, and market dynamics. Include inline references in format [chunk_X] immediately after specific facts or data points.",
    )


class ConsolidatedThreatItem(StructuredOutputResult):
    """A consolidated threat insight representing an external risk."""

    id: str = Field(..., description="Unique identifier for tracking this threat.")
    title: str = Field(
        ...,
        description="Clear, specific title that captures the essence of the external risk (e.g., 'Intensifying Competition from Well-Funded Rivals').",
    )
    bullet_points: list[ThreatBulletPoint] = Field(
        ...,
        min_length=2,
        description="Bullet points explaining the threat. Each focuses on a distinct aspect, dimension, or impact. Maintains an objective, evidence-based tone.",
    )


class ConsolidatedThreatsReport(StructuredOutputWithNotification):
    """Final aggregated report of threat insights from multiple batches."""

    threats: list[ConsolidatedThreatItem] = Field(
        ...,
        description="Refined, deduplicated set of threat insights representing all unique external risks. Should balance comprehensiveness with actionable clarity.",
    )

    def get_items(self) -> list[ConsolidatedThreatItem]:
        """Get the list of consolidated threat items."""
        return self.threats

    def update(self, new_items: Self) -> Self:
        """Merge new threat items into the report, updating matches by id."""
        existing_by_id = {item.id: item for item in self.threats}
        for new_item in new_items.threats:
            if new_item.id in existing_by_id:
                self._update_item(existing_by_id[new_item.id], new_item)
            else:
                self.threats.append(new_item)
        return self

    def _update_item(
        self,
        current_item: ConsolidatedThreatItem,
        new_item: ConsolidatedThreatItem,
    ) -> None:
        current_item.title = new_item.title
        current_item.bullet_points = new_item.bullet_points
