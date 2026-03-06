from typing import Annotated, Any, Protocol

from pydantic import Field

from core.google_search import GoogleSearch, GoogleSearchRequest
from core.schema import SearchEngineType, WebSearchResult
from core.vertexai import VertexAiRequest, VertexAISearchEngine


class SearchEngine(Protocol):
    def __init__(self, params: Any): ...

    async def search(self, query: str) -> list[WebSearchResult]: ...


SearchEngineRequestType = Annotated[
    GoogleSearchRequest | VertexAiRequest, Field(discriminator="search_engine")
]


def get_search_engine(search_engine_type: SearchEngineType) -> type[SearchEngine]:
    if search_engine_type == SearchEngineType.GOOGLE:
        return GoogleSearch
    elif search_engine_type == SearchEngineType.VERTEXAI:
        return VertexAISearchEngine
    else:
        raise ValueError(f"Invalid search engine type: {search_engine_type}")


__all__ = ["get_search_engine", "SearchEngineRequestType"]  # noqa: F401
