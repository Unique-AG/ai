from urllib.parse import urlparse

from pydantic import BaseModel, Field
from unique_toolkit.content import ContentReference


def extract_root_domain(url: str) -> str:
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    domain = domain.replace("www.", "")
    return domain


class WebSearchResult(BaseModel):
    url: str
    title: str
    snippet: str = Field(
        ...,
        description="A short description of the content found on this website",
    )
    content: str = Field(
        default="",
        description="The content of the website",
    )
    description: str = Field(
        default="",
        description="A short description of the content found on this website",
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
            description=self.snippet or "",
        )
