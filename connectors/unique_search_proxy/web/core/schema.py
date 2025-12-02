from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from enum import StrEnum

from typing import Generic, TypeVar


camelized_model_config = ConfigDict(alias_generator=to_camel)


class SearchEngineType(StrEnum):
    GOOGLE = "google"
    VERTEXAI = "vertexai"


T = TypeVar("T", bound=SearchEngineType)
U = TypeVar("U", bound=BaseModel)


# Pydantic Models
class SearchRequest(BaseModel, Generic[T, U]):
    """Request model for search endpoint."""

    model_config = camelized_model_config
    search_engine: T = Field(..., description="Search engine to use")

    query: str = Field(..., min_length=1, description="Search query string")

    timeout: int = Field(
        default=10, ge=1, le=600, description="The request timeout in seconds"
    )

    params: U = Field(
        ..., description="Additional keyword arguments for the search engine"
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
