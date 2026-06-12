from __future__ import annotations

from typing import Literal

from pydantic import Field

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles


class BasicCrawlRequest(BaseCrawlerConfig[CrawlerType.BASIC]):
    """Flat ``POST /v1/crawl`` body for the HTTP basic crawler."""

    crawler: Literal[CrawlerType.BASIC] = CrawlerType.BASIC

    content_types: ContentTypeToggles = Field(
        default_factory=ContentTypeToggles,
        title="Content types",
        description=(
            "Enable built-in processing per media type. "
            "Unchecked types return raw body only."
        ),
    )
    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=50,
        title="Maximum concurrent HTTP fetches",
        description="Maximum concurrent HTTP fetches",
    )


__all__ = [
    "BasicCrawlRequest",
]
