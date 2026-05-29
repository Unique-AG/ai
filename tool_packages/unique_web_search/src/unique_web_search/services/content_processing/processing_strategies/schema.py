from pydantic import BaseModel, ConfigDict, Field

from unique_web_search.services.content_processing.processing_strategies.base import (
    WebSearchResult,
)


class LLMProcessorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snippet: str = Field(
        description="A short, self-contained excerpt (2-3 sentences) capturing the most relevant finding from the page in relation to the search query.",
    )
    summary: str = Field(
        description=(
            "A comprehensive summary of the page content focused on information relevant to the search query. "
            "Preserves key facts, data points, dates, statistics, and conclusions. "
            "Always include labeled data fields and structured key-value pairs — "
            "they are factual data, not boilerplate, and are frequently the direct answer to the query."
        ),
    )

    def apply_to_page(self, page: WebSearchResult) -> WebSearchResult:
        page.snippet = self.snippet
        page.content = self.summary
        return page
