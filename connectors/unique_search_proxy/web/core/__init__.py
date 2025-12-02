from core.google_search import GoogleSearch, GoogleSearchRequest
from core.vertexai import VertexAISearchEngine, VertexAiRequest
from core.schema import SearchEngineType, WebSearchResult
from typing import Protocol, Any, Annotated
from pydantic import Field


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


__all__ = ["get_search_engine", "SearchEngineRequestType"]
