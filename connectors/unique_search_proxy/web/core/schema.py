from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from enum import StrEnum


camelized_model_config = ConfigDict(alias_generator=to_camel)


class SearchEngineType(StrEnum):
    GOOGLE = "google"
    VERTEXAI = "vertexai"


# Pydantic Models
class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    model_config = camelized_model_config

    search_engine: SearchEngineType = Field(..., description="Search engine to use")
    query: str = Field(..., min_length=1, description="Search query string")
    params: dict = Field(
        default_factory=dict,
        description="Additional keyword arguments for the search engine",
    )


class WebSearchResult(BaseModel):
    """Result model for a web search."""

    model_config = camelized_model_config

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


class WebSearchResults(BaseModel):
    """Results model for a web search."""

    model_config = camelized_model_config

    results: list[WebSearchResult]
