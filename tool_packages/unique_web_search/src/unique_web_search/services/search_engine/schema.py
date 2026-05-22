from pydantic import BaseModel, Field
from unique_toolkit.content import ContentReference

from unique_web_search.services.helpers import extract_root_domain


class WebSearchResult(BaseModel):
    url: str = Field(
        ...,
        description="The URL of the website",
    )
    title: str = Field(
        ...,
        description="The title of the website",
    )
    snippet: str = Field(
        ...,
        description="A short description of the content found on this website",
    )
    content: str = Field(
        default="",
        description="The content of the website",
    )
    relevance_score: float | None = Field(
        default=None,
        description=(
            "LLM-judge relevance score (0.0–1.0) attached when the SERP filter "
            "ran successfully. Higher = stronger match to the active gap/objective "
            "per the snippet-judge calibration bands. None when the filter was "
            "disabled, the LLM call failed, or this is a raw (unfiltered) result."
        ),
    )

    @property
    def display_link(self):
        return extract_root_domain(self.url)

    def to_content_reference(self, sequence_number: int) -> ContentReference:
        return ContentReference(
            name=self.title,
            url=self.url,
            sequence_number=sequence_number,
            source="WebSearch",
            source_id=self.url,
        )


class WebSearchResults(BaseModel):
    results: list[WebSearchResult]
