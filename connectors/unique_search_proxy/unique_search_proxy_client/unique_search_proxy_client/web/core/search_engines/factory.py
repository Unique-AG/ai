from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unique_search_proxy_core.search_engines.base import SearchEngine, SearchEngineType

from unique_search_proxy_client.web.core.search_engines.brave.service import (
    BraveSearchService,
)
from unique_search_proxy_client.web.core.search_engines.google.service import (
    GoogleSearchService,
)
from unique_search_proxy_client.web.core.search_engines.perplexity.service import (
    PerplexitySearchService,
)

if TYPE_CHECKING:
    from httpx import AsyncClient


def get_search_engine_service(
    engine: SearchEngineType,
    *,
    http_client: AsyncClient | None = None,
) -> SearchEngine[Any]:
    """Instantiate a search engine by registered id (deployment secrets from env)."""
    match engine:
        case SearchEngineType.GOOGLE:
            return GoogleSearchService(http_client=http_client)
        case SearchEngineType.BRAVE:
            return BraveSearchService(http_client=http_client)
        case SearchEngineType.PERPLEXITY:
            return PerplexitySearchService(http_client=http_client)
        case _:
            raise ValueError(f"Unsupported search engine: {engine}")


__all__ = [
    "get_search_engine_service",
]
