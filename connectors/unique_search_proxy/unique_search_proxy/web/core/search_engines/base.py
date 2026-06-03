from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from unique_search_proxy.web.core.schema import SearchEngineConfig, WebSearchResult


class SearchEngine(ABC):
    """Search engine contract for v1 providers."""

    engine_id: str

    def __init__(self, config: SearchEngineConfig) -> None:
        self.config = config

    @property
    @abstractmethod
    def snippet_only(self) -> bool:
        """When true, results need a crawler when includeContent is set."""

    @property
    @abstractmethod
    def mode(self) -> str:
        """Provider mode identifier for observability."""

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        fetch_size: int | None = None,
        timeout: int,
    ) -> tuple[Any, list[WebSearchResult]]:
        """Return provider raw payload and curated results."""
