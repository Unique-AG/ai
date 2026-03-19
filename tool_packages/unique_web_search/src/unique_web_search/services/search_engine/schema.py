from urllib.parse import urlparse

from pydantic import BaseModel, Field
from unique_toolkit.content import ContentReference

COMMON_SECOND_LEVEL_SUFFIXES = {
    "ac.uk",
    "co.in",
    "co.jp",
    "co.uk",
    "com.au",
    "com.br",
    "com.cn",
    "com.mx",
    "com.tr",
    "com.tw",
    "gov.uk",
    "net.au",
    "org.au",
    "org.uk",
}


def extract_root_domain(url: str) -> str:
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    domain = domain.split(":")[0]
    domain = domain.replace("www.", "")
    return domain


def extract_registered_domain(url: str) -> str:
    """Best-effort registrable-domain extraction for diversity grouping.

    This intentionally avoids adding a new dependency. It is highly reliable for
    common domains like `example.com` and for common second-level public suffixes
    such as `co.uk`, while remaining a heuristic for more exotic suffixes.
    """

    domain = extract_root_domain(url)
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain

    last_two = ".".join(parts[-2:])
    if last_two in COMMON_SECOND_LEVEL_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])

    if len(parts[-1]) == 2 and parts[-2] in {
        "ac",
        "co",
        "com",
        "edu",
        "gov",
        "net",
        "org",
    }:
        return ".".join(parts[-3:])

    return ".".join(parts[-2:])


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
