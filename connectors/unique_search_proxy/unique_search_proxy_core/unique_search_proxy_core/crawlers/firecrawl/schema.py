from __future__ import annotations

from typing import Literal

from pydantic import Field

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.projection import build_crawl_request_model

FirecrawlProxyMode = Literal["basic", "enhanced", "auto"]


class FirecrawlConfig(BaseCrawlerConfig[CrawlerType.FIRECRAWL]):
    """Deployment config for Firecrawl (scrape or batch scrape)."""

    crawler: Literal[CrawlerType.FIRECRAWL] = CrawlerType.FIRECRAWL

    only_main_content: bool = Field(
        default=True,
        title="Only main content",
        description="Exclude headers, navs, footers before markdown generation.",
    )
    only_clean_content: bool = Field(
        default=False,
        title="Only clean content",
        description="LLM pass to remove residual boilerplate from markdown.",
    )
    max_concurrency: int | None = Field(
        default=None,
        ge=1,
        title="Max concurrency",
        description="Maximum concurrent scrapes for this batch job.",
    )
    ignore_invalid_urls: bool = Field(
        default=True,
        title="Ignore invalid URLs",
        description="Skip invalid URLs instead of failing the whole batch.",
    )
    wait_for: int = Field(
        default=0,
        ge=0,
        title="Wait for",
        description="Extra delay in milliseconds before fetching page content.",
    )
    mobile: bool = Field(
        default=False,
        title="Mobile emulation",
        description="Emulate a mobile device when scraping.",
    )
    block_ads: bool = Field(
        default=True,
        title="Block ads",
        description="Enable ad-blocking and cookie-popup blocking.",
    )
    remove_base64_images: bool = Field(
        default=True,
        title="Remove base64 images",
        description="Strip base64 image data from markdown output.",
    )
    proxy: FirecrawlProxyMode = Field(
        default="auto",
        title="Proxy mode",
        description="Firecrawl proxy tier: `basic`, `enhanced`, or `auto`.",
    )
    include_tags: list[str] | None = Field(
        default=None,
        title="Include tags",
        description="HTML tags to include in scrape output.",
    )
    exclude_tags: list[str] | None = Field(
        default=None,
        title="Exclude tags",
        description="HTML tags to exclude from scrape output.",
    )
    scrape_headers: dict[str, str] | None = Field(
        default=None,
        title="Scrape headers",
        description="Headers sent to the target page (cookies, user-agent, etc.).",
    )
    max_age: int | None = Field(
        default=None,
        ge=0,
        title="Max age",
        description=(
            "Return cached page content younger than this age in milliseconds."
        ),
    )


FirecrawlCrawlRequest = build_crawl_request_model(FirecrawlConfig)


__all__ = [
    "FirecrawlConfig",
    "FirecrawlCrawlRequest",
    "FirecrawlProxyMode",
]
