from __future__ import annotations

from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.schema import DeactivatedNone

FirecrawlProxyMode = Literal["basic", "enhanced", "auto"]

MaxConcurrencyOrNone: TypeAlias = (
    Annotated[int, Field(title="Integer", ge=1)] | DeactivatedNone
)
TagListOrNone: TypeAlias = (
    Annotated[
        list[str],
        Field(title="Tags"),
        RJSFMetaTag({"ui:options": {"orderable": False}}),
    ]
    | DeactivatedNone
)
ScrapeHeadersOrNone: TypeAlias = (
    Annotated[dict[str, str], Field(title="Headers")] | DeactivatedNone
)
MaxAgeOrNone: TypeAlias = Annotated[int, Field(title="Integer", ge=0)] | DeactivatedNone


class FirecrawlConfig(BaseCrawlerConfig[CrawlerType.FIRECRAWL]):
    """Deployment config for Firecrawl (scrape or batch scrape)."""

    _request_model_name: ClassVar[str] = "FirecrawlCrawlRequest"

    crawler: Annotated[
        Literal[CrawlerType.FIRECRAWL], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=CrawlerType.FIRECRAWL,
        title="Crawler",
        description="Provider discriminator; must be `Firecrawl` for this config.",
    )

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
    max_concurrency: MaxConcurrencyOrNone = Field(
        default=None,
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
    include_tags: TagListOrNone = Field(
        default=None,
        title="Include tags",
        description="HTML tags to include in scrape output.",
    )
    exclude_tags: TagListOrNone = Field(
        default=None,
        title="Exclude tags",
        description="HTML tags to exclude from scrape output.",
    )
    scrape_headers: ScrapeHeadersOrNone = Field(
        default=None,
        title="Scrape headers",
        description="Headers sent to the target page (cookies, user-agent, etc.).",
    )
    max_age: MaxAgeOrNone = Field(
        default=None,
        title="Max age",
        description=(
            "Return cached page content younger than this age in milliseconds."
        ),
    )


FirecrawlCrawlRequest = FirecrawlConfig.request_model()


__all__ = [
    "FirecrawlConfig",
    "FirecrawlCrawlRequest",
    "FirecrawlProxyMode",
]
