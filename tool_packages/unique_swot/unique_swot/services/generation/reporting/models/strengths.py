from typing import Self

from pydantic import Field

from unique_swot.utils import (
    StructuredOutputResult,
    StructuredOutputWithNotification,
)


class StrengthBulletPoint(StructuredOutputResult):
    """A single bullet point within a strength insight."""

    key_reasoning: str = Field(
        ...,
        description="Bold summary that captures the core insight in plain language. Should be accessible to someone unfamiliar with the company.",
    )
    detailed_context: str = Field(
        ...,
        description="Detailed explanation with evidence and context. Define technical terms and abbreviations when first used. Include inline references in format [chunk_X] immediately after specific facts or data points.",
    )


class ConsolidatedStrengthItem(StructuredOutputResult):
    """A consolidated strength insight representing an internal advantage."""

    id: str = Field(..., description="Unique identifier for tracking this strength.")
    title: str = Field(
        ...,
        description="Clear, specific title that captures the essence of the competitive advantage (e.g., 'Leading Position in Digital Rewards with Walmart Partnership').",
    )
    bullet_points: list[StrengthBulletPoint] = Field(
        ...,
        min_length=2,
        description="Bullet points explaining the strength. Each focuses on a distinct aspect, dimension, or implication. First strength should introduce what the company does.",
    )


class ConsolidatedStrengthsReport(StructuredOutputWithNotification):
    """Final aggregated report of strength insights from multiple batches."""

    strengths: list[ConsolidatedStrengthItem] = Field(
        ...,
        description="Refined, deduplicated set of strength insights representing all unique internal advantages. First strength should introduce the company and its industry leadership position.",
    )

    def get_items(self) -> list[ConsolidatedStrengthItem]:
        """Get the list of consolidated strength items."""
        return self.strengths

    def update(self, new_items: Self) -> Self:
        """Merge new strength items into the report, updating matches by id."""
        existing_by_id = {item.id: item for item in self.strengths}
        for new_item in new_items.strengths:
            if new_item.id in existing_by_id:
                self._update_item(existing_by_id[new_item.id], new_item)
            else:
                self.strengths.append(new_item)
        return self

    def _update_item(
        self,
        current_item: ConsolidatedStrengthItem,
        new_item: ConsolidatedStrengthItem,
    ) -> None:
        current_item.title = new_item.title
        current_item.bullet_points = new_item.bullet_points
