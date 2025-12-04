from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class StrengthBulletPoint(BaseModel):
    """A single bullet point within a strength insight."""

    model_config = ConfigDict(extra="forbid")

    key_reasoning: str = Field(
        ...,
        description="Bold summary that captures the core insight in plain language. Should be accessible to someone unfamiliar with the company.",
    )
    detailed_context: str = Field(
        ...,
        description="Detailed explanation with evidence and context. Define technical terms and abbreviations when first used. Include inline references in format [chunk_X] immediately after specific facts or data points.",
    )


class ConsolidatedStrengthItem(BaseModel):
    """A consolidated strength insight representing an internal advantage."""

    model_config = ConfigDict(extra="forbid")

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


class ConsolidatedStrengthsReport(BaseModel):
    """Final aggregated report of strength insights from multiple batches."""

    model_config = ConfigDict(extra="forbid")

    strengths: list[ConsolidatedStrengthItem] = Field(
        ...,
        description="Refined, deduplicated set of strength insights representing all unique internal advantages. First strength should introduce the company and its industry leadership position.",
    )

    def get_items(self) -> list[ConsolidatedStrengthItem]:
        """Get the list of consolidated strength items."""
        return self.strengths

    def update(self, new_items: Self) -> Self:
        new_items_by_id = {item.id: item for item in new_items.strengths}
        for item in self.strengths:
            if item.id in new_items_by_id:
                self._update_item(new_items_by_id[item.id])
            else:
                self.strengths.append(item)
        return self

    def _update_item(
        self,
        new_item: ConsolidatedStrengthItem,
    ) -> None:
        self.title = new_item.title
        self.bullet_points = new_item.bullet_points
