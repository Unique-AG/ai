from enum import StrEnum

from pydantic import BaseModel


class SourceType(StrEnum):
    """Enumeration of supported data source types for SWOT analysis."""

    WEB_SEARCH = "web_search"
    INTERNAL_DOCUMENT = "internal_document"
    EARNINGS_CALL = "earnings_call"


class SourceChunk(BaseModel):
    id: str
    text: str


class Source(BaseModel):
    """
    Represents a data source used in SWOT analysis.

    Attributes:
        source_id: Unique identifier for the source
        type: The type of data source (web search, internal document, etc.)
        content: The actual content/text from the source
    """

    type: SourceType
    url: str | None
    title: str
    chunks: list[SourceChunk]
