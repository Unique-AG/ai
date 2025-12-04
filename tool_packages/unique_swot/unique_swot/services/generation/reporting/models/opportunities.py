from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class OpportunityBulletPoint(BaseModel):
    """A single bullet point within an opportunity insight."""

    model_config = ConfigDict(extra="forbid")

    key_reasoning: str = Field(
        ...,
        description="Bold summary that frames the specific aspect of the opportunity being discussed. Should be concise but complete.",
    )
    detailed_context: str = Field(
        ...,
        description="Detailed explanation including background, growth drivers, projections, and company-specific benefits. Include inline references in format [chunk_X] immediately after specific facts or data points.",
    )


class ConsolidatedOpportunityItem(BaseModel):
    """A consolidated opportunity insight representing a broader theme or trend."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for tracking this opportunity.")
    title: str = Field(
        ...,
        description="Clear, specific title that captures the broader theme or trend (e.g., 'Expanding Beyond Walmart to Capture Multi-Retailer Market').",
    )
    bullet_points: list[OpportunityBulletPoint] = Field(
        ...,
        min_length=2,
        description="Narrative-driven bullet points that build on each other. Start with context/background, explain the market opportunity, then show how the company can capitalize.",
    )


class ConsolidatedOpportunitiesReport(BaseModel):
    """Final aggregated report of opportunity insights from multiple batches."""

    model_config = ConfigDict(extra="forbid")

    opportunities: list[ConsolidatedOpportunityItem] = Field(
        ...,
        description="Refined, deduplicated set of opportunity insights representing all unique external favorable conditions. Should be comprehensive, well-organized, and easy to follow.",
    )

    def get_items(self) -> list[ConsolidatedOpportunityItem]:
        """Get the list of consolidated opportunity items."""
        return self.opportunities

    def update(self, new_items: Self) -> Self:
        new_items_by_id = {item.id: item for item in new_items.opportunities}
        for item in self.opportunities:
            if item.id in new_items_by_id:
                self._update_item(new_items_by_id[item.id])
            else:
                self.opportunities.append(item)
        return self

    def _update_item(
        self,
        new_item: ConsolidatedOpportunityItem,
    ) -> None:
        self.title = new_item.title
        self.bullet_points = new_item.bullet_points
