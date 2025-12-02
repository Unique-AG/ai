from typing import Protocol
from pydantic import BaseModel
from core.schema import WebSearchResult, SearchEngineType
from typing import Any
from core.google_search import GoogleSearch, GoogleSearchParams
from core.vertexai import VertexAISearchEngine, VertexAiParams


class SearchEngine(Protocol):
    def __init__(self, params: Any): ...

    async def search(self, query: str) -> list[WebSearchResult]: ...


type SearchEngineFactory = tuple[type[SearchEngine], type[BaseModel]]


class CoreFactory:
    def __init__(self):
        self.search_engine_factory: dict[SearchEngineType, SearchEngineFactory] = {}

    def register(
        self,
        *,
        search_engine_type: SearchEngineType,
        search_engine_factory: type[SearchEngine],
        params: type[BaseModel],
    ):
        self.search_engine_factory[search_engine_type] = (search_engine_factory, params)

    def resolve(self, search_engine_type: SearchEngineType) -> SearchEngineFactory:
        return self.search_engine_factory[search_engine_type]


core_factory = CoreFactory()

core_factory.register(
    search_engine_type=SearchEngineType.GOOGLE,
    search_engine_factory=GoogleSearch,
    params=GoogleSearchParams,
)

core_factory.register(
    search_engine_type=SearchEngineType.VERTEXAI,
    search_engine_factory=VertexAISearchEngine,
    params=VertexAiParams,
)
