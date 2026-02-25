from typing import NotRequired, Protocol, TypedDict, Unpack

from unique_web_search.services.search_engine.schema import WebSearchResult


class ProcessingStrategyKwargs(TypedDict):
    page: WebSearchResult
    query: NotRequired[str]


class ProcessingStrategy(Protocol):
    async def __call__(
        self, **kwargs: Unpack[ProcessingStrategyKwargs]
    ) -> WebSearchResult: ...

    @property
    def is_enabled(self) -> bool: ...


class CleaningStrategy(Protocol):
    def __call__(self, content: str) -> str: ...

    @property
    def is_enabled(self) -> bool: ...
