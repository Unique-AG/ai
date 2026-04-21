"""V3 WebSearch tool parameters: exactly one of ``search`` or ``read`` per invocation."""

from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class WebSearchV3CommandType(StrEnum):
    SEARCH = "search"
    FETCH_URLS = "fetch_urls"


T = TypeVar("T", bound=WebSearchV3CommandType)


class WebSearchV3BaseCommand(BaseModel, Generic[T]):
    """Base command for the V3 WebSearch tool."""

    model_config = ConfigDict(extra="forbid")
    command: T


class WebSearchV3SearchCommand(WebSearchV3BaseCommand[WebSearchV3CommandType.SEARCH]):
    """Run a web search; results return as content chunks (e.g. snippets)."""

    command: Literal[WebSearchV3CommandType.SEARCH]

    objective: str = Field(description="What you are trying to find out.")
    query: str = Field(description="Search query for the configured search engine.")


class WebSearchV3FetchUrlsCommand(
    WebSearchV3BaseCommand[WebSearchV3CommandType.FETCH_URLS]
):
    """Fetch full pages for the given URLs (typically after a prior search call)."""

    command: Literal[WebSearchV3CommandType.FETCH_URLS]

    objective: str = Field(description="Why these URLs are being fetched.")
    urls: list[str] = Field(
        min_length=1,
        description="HTTP(S) URLs to crawl.",
    )


class WebSearchV3ToolParameters(BaseModel):
    """Root JSON for the V3 WebSearch tool: discriminated union on ``command``."""
    model_config = ConfigDict(extra="forbid")
    exec: WebSearchV3SearchCommand | WebSearchV3FetchUrlsCommand = Field(
        discriminator="command", description="The command to execute."
    )
