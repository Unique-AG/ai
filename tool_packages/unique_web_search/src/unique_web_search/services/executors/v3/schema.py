"""V3 WebSearch tool parameters: a flat schema with exactly one of ``query`` or ``urls`` per call."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Command(StrEnum):
    SEARCH = "search"
    FETCH_URLS = "read_urls"


class SearchPayload(BaseModel):
    gap: str = Field(
        description="A brief description of the gap that the query is meant to fill"
    )
    query: str = Field(
        description="Search query for the configured search engine. Query must be fixed for the entire rounds."
    )


class FetchUrlsPayload(BaseModel):
    urls: list[str] = Field(
        description="HTTP(S) URLs to crawl for full-page text. Use only URLs returned by a prior search or pasted by the user."
    )


class WebSearchV3ToolParameters(BaseModel):
    """Root JSON for the V3 WebSearch tool: set exactly one of ``query`` or ``urls``."""

    model_config = ConfigDict(extra="forbid")

    command: Command = Field(
        description="The command to execute. Must be either 'search' or 'read_urls'."
    )

    objective: str = Field(
        description="One concise sentence: what this call is meant to accomplish."
    )
    
    payload: SearchPayload | FetchUrlsPayload = Field(description="The payload of the command. Must be either a SearchPayload or a FetchUrlsPayload.")
    
    
    def get_display_name_suffix(self) -> str:
        if self.command == Command.SEARCH:
            return " - Searching"
        elif self.command == Command.FETCH_URLS:
            return " - Reading Pages"
        else:
            raise ValueError(f"Invalid command: {self.command}")

