from __future__ import annotations

from typing import TYPE_CHECKING, Generic

from unique_search_proxy_core.search_engines.base import SearchEngine, SearchRequestT

if TYPE_CHECKING:
    from httpx import AsyncClient


class SearchEngineService(SearchEngine[SearchRequestT], Generic[SearchRequestT]):
    """Client-side search engine base (HTTP client wiring)."""

    def __init__(
        self,
        *,
        http_client: AsyncClient | None = None,
    ) -> None:
        super().__init__(http_client=http_client)
