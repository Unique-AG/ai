from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel
from unique_search_proxy_core.schema import CrawlUrlResult

from unique_search_proxy_client.web.core.url_safety.gate import AllowedCrawlTarget


@runtime_checkable
class PinnedEgressCrawler(Protocol):
    """Crawlers that fetch directly and must reuse gate DNS resolution."""

    async def crawl_pinned(
        self,
        request: BaseModel,
        allowed_targets: list[AllowedCrawlTarget],
    ) -> list[CrawlUrlResult]: ...


__all__ = ["PinnedEgressCrawler"]
