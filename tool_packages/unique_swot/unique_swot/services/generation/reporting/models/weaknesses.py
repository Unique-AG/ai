from typing import Self

from pydantic import Field

from unique_swot.utils import (
    StructuredOutputResult,
    StructuredOutputWithNotification,
)


class WeaknessBulletPoint(StructuredOutputResult):
    """A single bullet point within a weakness insight."""

    key_reasoning: str = Field(
        ...,
        description="Bold summary that captures the core limitation in direct, factual language. Should avoid judgmental tone while being clear about the issue.",
    )
    detailed_context: str = Field(
        ...,
        description="Detailed explanation with evidence and industry context. Define technical terms, abbreviations, and metrics (e.g., 'EBITDA margin of -8% vs. industry average of +12%'). Include inline references in format [chunk_X] immediately after specific facts or data points.",
    )


class ConsolidatedWeaknessItem(StructuredOutputResult):
    """A consolidated weakness insight representing an internal limitation."""

    id: str = Field(..., description="Unique identifier for tracking this weakness.")
    title: str = Field(
        ...,
        description="Clear, specific title that captures the essence of the limitation (e.g., 'Profitability Challenges and Path to Break-Even').",
    )
    bullet_points: list[WeaknessBulletPoint] = Field(
        ...,
        min_length=2,
        description="Bullet points explaining the weakness. Each focuses on a distinct aspect, dimension, or consequence. Maintains an objective, constructive tone.",
    )


class ConsolidatedWeaknessesReport(StructuredOutputWithNotification):
    """Final aggregated report of weakness insights from multiple batches."""

    weaknesses: list[ConsolidatedWeaknessItem] = Field(
        ...,
        description="Refined, deduplicated set of weakness insights representing all unique internal limitations. Should be comprehensive yet concise, maintaining a constructive perspective.",
    )

    def get_items(self) -> list[ConsolidatedWeaknessItem]:
        """Get the list of consolidated weakness items."""
        return self.weaknesses

    def update(self, new_items: Self) -> Self:
        """Merge new weakness items into the report, updating matches by id."""
        existing_by_id = {item.id: item for item in self.weaknesses}
        for new_item in new_items.weaknesses:
            if new_item.id in existing_by_id:
                self._update_item(existing_by_id[new_item.id], new_item)
            else:
                self.weaknesses.append(new_item)
        return self

    def _update_item(
        self,
        current_item: ConsolidatedWeaknessItem,
        new_item: ConsolidatedWeaknessItem,
    ) -> None:
        current_item.title = new_item.title
        current_item.bullet_points = new_item.bullet_points
