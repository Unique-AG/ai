from __future__ import annotations

from typing import Literal

from pydantic import Field

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver


class BasicConfig(BaseCrawlerConfig[CrawlerType.BASIC]):
    """Deployment config for the HTTP basic crawler."""

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


BasicCrawlRequest = ConfigRequestResolver.crawl_request_model(BasicConfig)


__all__ = [
    "BasicConfig",
    "BasicCrawlRequest",
]
