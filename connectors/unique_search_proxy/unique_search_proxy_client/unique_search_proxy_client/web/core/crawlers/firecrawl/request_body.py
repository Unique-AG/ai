from __future__ import annotations

from typing import Any

from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlCrawlRequest,
)

from unique_search_proxy_client.web.core.firecrawl_parsers import firecrawl_parsers

_MS_PER_SECOND = 1000


def _firecrawl_common_scrape_fields(
    request: FirecrawlCrawlRequest,  # type: ignore[valid-type]
    *,
    zero_data_retention: bool,
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
    }
    if request.proxy != "auto":
        body["proxy"] = request.proxy
    # The next three are sent only when they differ from Firecrawl's default.
    if not request.store_in_cache:
        body["storeInCache"] = False
    if request.skip_tls_verification:
        body["skipTlsVerification"] = True
    location = _location(request)
    if location is not None:
        body["location"] = location

    if request.include_tags is not None:
        body["includeTags"] = request.include_tags
    if request.exclude_tags is not None:
        body["excludeTags"] = request.exclude_tags
    if request.scrape_headers is not None:
        body["headers"] = request.scrape_headers
    body["maxAge"] = _max_age_ms(request)
    body["parsers"] = firecrawl_parsers(request.max_pdf_pages, request.pdf_mode)
    # Sent only when on: accounts without zero data retention reject the field.
    if zero_data_retention:
        body["zeroDataRetention"] = True

    return body


def _max_age_ms(
    request: FirecrawlCrawlRequest,  # type: ignore[valid-type]
) -> int:
    # A caller that sends only the deprecated ``max_age`` means that value, not
    # the default of the field that replaced it.
    legacy_ms: int | None = request.max_age
    if legacy_ms is not None and (
        "max_cache_age_seconds" not in request.model_fields_set
    ):
        return legacy_ms
    return request.max_cache_age_seconds * _MS_PER_SECOND


def _location(
    request: FirecrawlCrawlRequest,  # type: ignore[valid-type]
) -> dict[str, Any] | None:
    location: dict[str, Any] = {}
    if request.country is not None:
        location["country"] = request.country
    if request.languages:
        location["languages"] = request.languages
    return location or None


def build_firecrawl_scrape_body(
    url: str,
    request: FirecrawlCrawlRequest,  # type: ignore[valid-type]
    *,
    zero_data_retention: bool = False,
) -> dict[str, Any]:
    """Build Firecrawl ``POST /v2/scrape`` JSON body for a single URL."""
    body = _firecrawl_common_scrape_fields(
        request, zero_data_retention=zero_data_retention
    )
    body["url"] = url
    return body


def build_firecrawl_batch_scrape_body(
    urls: list[str],
    request: FirecrawlCrawlRequest,  # type: ignore[valid-type]
    *,
    zero_data_retention: bool = False,
) -> dict[str, Any]:
    """Build Firecrawl ``POST /v2/batch/scrape`` JSON body."""
    body = _firecrawl_common_scrape_fields(
        request, zero_data_retention=zero_data_retention
    )
    body["urls"] = urls
    body["ignoreInvalidURLs"] = request.ignore_invalid_urls

    if request.max_concurrency is not None:
        body["maxConcurrency"] = request.max_concurrency

    return body
