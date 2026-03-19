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
