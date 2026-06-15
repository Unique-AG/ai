from __future__ import annotations

from typing import Any

from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlCrawlRequest,
)


def _firecrawl_common_scrape_fields(
    request: FirecrawlCrawlRequest,
) -> dict[str, Any]:
    scrape_timeout_ms = min(max(request.timeout * 1000, 1000), 300_000)
    body: dict[str, Any] = {
        "formats": [{"type": "markdown"}],
        "timeout": scrape_timeout_ms,
        "onlyMainContent": request.only_main_content,
        "onlyCleanContent": request.only_clean_content,
        "waitFor": request.wait_for,
        "mobile": request.mobile,
        "blockAds": request.block_ads,
        "removeBase64Images": request.remove_base64_images,
        "proxy": request.proxy,
    }

    if request.include_tags is not None:
        body["includeTags"] = request.include_tags
    if request.exclude_tags is not None:
        body["excludeTags"] = request.exclude_tags
    if request.scrape_headers is not None:
        body["headers"] = request.scrape_headers
    if request.max_age is not None:
        body["maxAge"] = request.max_age

    return body


def build_firecrawl_scrape_body(
    url: str,
    request: FirecrawlCrawlRequest,
) -> dict[str, Any]:
    """Build Firecrawl ``POST /v2/scrape`` JSON body for a single URL."""
    body = _firecrawl_common_scrape_fields(request)
    body["url"] = url
    return body


def build_firecrawl_batch_scrape_body(
    urls: list[str],
    request: FirecrawlCrawlRequest,
) -> dict[str, Any]:
    """Build Firecrawl ``POST /v2/batch/scrape`` JSON body."""
    body = _firecrawl_common_scrape_fields(request)
    body["urls"] = urls
    body["ignoreInvalidURLs"] = request.ignore_invalid_urls

    if request.max_concurrency is not None:
        body["maxConcurrency"] = request.max_concurrency

    return body
