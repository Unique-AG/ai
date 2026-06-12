from __future__ import annotations

from typing import Any

from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlCrawlRequest,
)


def build_firecrawl_batch_scrape_body(
    urls: list[str],
    request: FirecrawlCrawlRequest,
) -> dict[str, Any]:
    """Build Firecrawl ``POST /v2/batch/scrape`` JSON body."""
    scrape_timeout_ms = min(max(request.timeout * 1000, 1000), 300_000)
    body: dict[str, Any] = {
        "urls": urls,
        "formats": [{"type": "markdown"}],
        "timeout": scrape_timeout_ms,
        "onlyMainContent": request.only_main_content,
        "onlyCleanContent": request.only_clean_content,
        "ignoreInvalidURLs": request.ignore_invalid_urls,
        "waitFor": request.wait_for,
        "mobile": request.mobile,
        "blockAds": request.block_ads,
        "removeBase64Images": request.remove_base64_images,
        "proxy": request.proxy,
    }

    if request.max_concurrency is not None:
        body["maxConcurrency"] = request.max_concurrency
    if request.include_tags is not None:
        body["includeTags"] = request.include_tags
    if request.exclude_tags is not None:
        body["excludeTags"] = request.exclude_tags
    if request.scrape_headers is not None:
        body["headers"] = request.scrape_headers
    if request.max_age is not None:
        body["maxAge"] = request.max_age

    return body
