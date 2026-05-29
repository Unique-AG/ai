from pydantic import BaseModel, Field, field_validator
from unique_toolkit.content import ContentReference

from unique_web_search.services.helpers import extract_root_domain
from unique_web_search.services.text_sanitize import (
    sanitize_single_line,
    strip_controls,
)


class WebSearchResult(BaseModel):
    """The single ingress point for external text into the web-search pipeline.

    Every search engine adapter and the ``read_urls`` crawler path constructs
    a ``WebSearchResult`` before any downstream consumer (chunker, content
    processor, debug payload, tool result) sees the data. The field validators
    below strip ASCII control characters at this boundary — most importantly
    the NUL byte (``\\u0000``), which Postgres TEXT columns reject with error
    ``22P05`` and which would otherwise poison every subsequent message write
    once the dirty string lands in a tool result.

    Sanitizing here rather than at every downstream call site means no consumer
    needs to defensively re-sanitize: by the time a ``WebSearchResult``
    exists, it is safe to embed in JSON, SQL, or chunk metadata.
    """

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

    # Short, strictly-single-line fields — replace controls with space and
    # collapse whitespace. URLs cannot legitimately span lines; titles in
    # practice are one-line. Empty string is fine (``read_urls`` passes
    # ``title=""``).
    @field_validator("url", "title", mode="before")
    @classmethod
    def _sanitize_short_field(cls, v: object) -> object:
        if isinstance(v, str):
            return sanitize_single_line(v)
        return v

    # ``snippet`` and ``content`` may legitimately carry newlines — some
    # engines (Brave, Bing grounding) join multiple sub-snippets with ``\n``,
    # and crawled page bodies preserve paragraph structure. Strip controls
    # only; keep TAB/LF/CR.
    @field_validator("snippet", "content", mode="before")
    @classmethod
    def _sanitize_long_field(cls, v: object) -> object:
        if isinstance(v, str):
            return strip_controls(v)
        return v

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
