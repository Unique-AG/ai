from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles
from unique_search_proxy_core.projection import build_crawl_request_model
from unique_search_proxy_core.schema import get_model_config


class BasicCrawlerCall(BaseModel):
    """LLM-facing call surface for the basic crawler (urls supplied per invocation)."""

    urls: list[str] = Field(
        ...,
        min_length=1,
        description="URLs to fetch and convert to markdown",
    )


class BasicCrawlerConfig(BaseCrawlerConfig[CrawlerType.BASIC]):
    """Deployment config for the HTTP basic crawler."""

    model_config = get_model_config(title="Basic Proxy Crawler ")

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


def basic_crawler_request_model() -> type[BaseModel]:
    """Derived ``POST /v1/crawl`` model (cached via ``build_crawl_request_model``)."""
    return build_crawl_request_model(BasicCrawlerConfig)


BasicCrawlerRequest = basic_crawler_request_model()


__all__ = [
    "BasicCrawlerCall",
    "BasicCrawlerConfig",
    "BasicCrawlerRequest",
    "basic_crawler_request_model",
]
