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

    notification_message: str = Field(
        description="A message to be displayed to the user to keep him updated on the progress of the reporting"
    )

    opportunities: list[ConsolidatedOpportunityItem] = Field(
        ...,
        description="Refined, deduplicated set of opportunity insights representing all unique external favorable conditions. Should be comprehensive, well-organized, and easy to follow.",
    )

    def get_items(self) -> list[ConsolidatedOpportunityItem]:
        """Get the list of consolidated opportunity items."""
        return self.opportunities

    def update(self, new_items: Self) -> Self:
        """Merge new opportunity items into the report, updating matches by id."""
        existing_by_id = {item.id: item for item in self.opportunities}
        for new_item in new_items.opportunities:
            if new_item.id in existing_by_id:
                self._update_item(existing_by_id[new_item.id], new_item)
            else:
                self.opportunities.append(new_item)
        return self

    def _update_item(
        self,
        current_item: ConsolidatedOpportunityItem,
        new_item: ConsolidatedOpportunityItem,
    ) -> None:
        current_item.title = new_item.title
        current_item.bullet_points = new_item.bullet_points
