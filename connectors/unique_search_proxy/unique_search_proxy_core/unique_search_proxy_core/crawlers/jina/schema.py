from __future__ import annotations

from typing import Literal

from pydantic import Field

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.projection import build_crawl_request_model

JinaReturnFormat = Literal["markdown", "html", "text", "screenshot", "pageshot"]
JinaEngine = Literal["auto", "browser", "direct", "cf-browser-rendering"]
JinaRetainImages = Literal["none", "all", "alt", "all_p", "alt_p"]


class JinaConfig(BaseCrawlerConfig[CrawlerType.JINA]):
    """Deployment config for the Jina Reader crawler."""

    crawler: Literal[CrawlerType.JINA] = CrawlerType.JINA

    return_format: JinaReturnFormat = Field(
        default="markdown",
        title="Return format",
        description=(
            "Jina Reader output format: `markdown`, `html`, `text`, `screenshot`, "
            "or `pageshot`."
        ),
    )
    engine: JinaEngine = Field(
        default="browser",
        title="Engine",
        description=(
            "`browser` for best quality, `direct` for speed, "
            "`cf-browser-rendering` for JS-heavy sites."
        ),
    )
    page_timeout: int | None = Field(
        default=None,
        ge=1,
        le=180,
        title="Page load timeout",
        description=(
            "Max seconds to wait for the page to load (Jina Reader). "
            "Defaults to the crawl `timeout` when unset."
        ),
    )
    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=50,
        title="Maximum concurrent reader requests",
        description="Maximum concurrent Jina Reader POST requests.",
    )
    no_cache: bool = Field(
        default=False,
        title="Bypass cache",
        description="Bypass Jina cache and fetch fresh content.",
    )
    target_selector: list[str] | None = Field(
        default=None,
        title="Target selector",
        description="CSS selectors to focus extraction on specific page elements.",
    )
    wait_for_selector: list[str] | None = Field(
        default=None,
        title="Wait for selector",
        description="CSS selectors to wait for before returning content.",
    )
    remove_selector: list[str] | None = Field(
        default=None,
        title="Remove selector",
        description="CSS selectors for page regions to strip (headers, footers, etc.).",
    )
    with_generated_alt: bool = Field(
        default=False,
        title="Generated alt text",
        description="Generate alt text for images missing alt tags.",
    )
    with_links_summary: bool = Field(
        default=False,
        title="Links summary",
        description="Include a links summary in the reader response.",
    )
    with_images_summary: bool = Field(
        default=False,
        title="Images summary",
        description="Include an images summary in the reader response.",
    )
    with_iframe: bool = Field(
        default=False,
        title="Include iframes",
        description="Include iframe content in the reader response.",
    )
    retain_images: JinaRetainImages | None = Field(
        default=None,
        title="Retain images",
        description="Control which images are retained in markdown output.",
    )
    locale: str | None = Field(
        default=None,
        title="Locale",
        description="Browser locale used to render the page (e.g. `en-US`).",
    )
    referer: str | None = Field(
        default=None,
        title="Referer",
        description="Referer header sent when fetching the target URL.",
    )
    proxy_url: str | None = Field(
        default=None,
        title="Proxy URL",
        description="Proxy URL used by Jina Reader to access the target page.",
    )
    do_not_track: bool = Field(
        default=True,
        title="Do not track",
        description="Send DNT (Do Not Track) to the reader service.",
    )


JinaCrawlRequest = build_crawl_request_model(JinaConfig)


__all__ = [
    "JinaConfig",
    "JinaCrawlRequest",
    "JinaEngine",
    "JinaRetainImages",
    "JinaReturnFormat",
]
