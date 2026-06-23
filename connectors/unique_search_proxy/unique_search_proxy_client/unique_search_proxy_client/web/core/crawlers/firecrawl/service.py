from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from unique_search_proxy_core.crawlers.base import BaseCrawler, CrawlerType
from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlCrawlRequest,
)
from unique_search_proxy_core.schema import CrawlUrlResult

from unique_search_proxy_client.web.core.crawlers.firecrawl.polling import (
    poll_batch_scrape,
)
from unique_search_proxy_client.web.core.crawlers.firecrawl.request_body import (
    build_firecrawl_batch_scrape_body,
    build_firecrawl_scrape_body,
)
from unique_search_proxy_client.web.core.provider_response import (
    crawl_upstream_error,
    raise_batch_upstream_failure,
    transport_error_raw,
    upstream_error_message,
    upstream_response_raw,
)
from unique_search_proxy_client.web.settings.providers.firecrawl import (
    firecrawl_crawl_credentials as credentials,
)
from unique_search_proxy_client.web.settings.secret_str import read_secret
from unique_search_proxy_client.web.utils.url import join_url_path

_LOGGER = logging.getLogger(__name__)
_FIRECRAWL_PROVIDER_LABEL = "Firecrawl"


def _firecrawl_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


class FirecrawlCrawlerService(BaseCrawler[FirecrawlCrawlRequest]):
    """Firecrawl crawler: single URL via scrape, multiple via batch scrape + poll."""

    crawler_id = CrawlerType.FIRECRAWL.value

    async def crawl(self, request: FirecrawlCrawlRequest) -> list[CrawlUrlResult]:  # type: ignore[override]
        credentials.check_credentials()

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Firecrawl crawler")

        urls = list(request.urls)
        timeout = request.timeout
        deadline = time.monotonic() + timeout

        if len(urls) == 1:
            return [
                await self._scrape_single_url(
                    client,
                    url=urls[0],
                    request=request,
                    timeout=timeout,
                ),
            ]

        return await self._batch_scrape_urls(
            client,
            urls=urls,
            request=request,
            timeout=timeout,
            deadline=deadline,
        )

    async def _scrape_single_url(
        self,
        client: httpx.AsyncClient,
        *,
        url: str,
        request: FirecrawlCrawlRequest,  # type: ignore[valid-type]
        timeout: int,
    ) -> CrawlUrlResult:
        body = build_firecrawl_scrape_body(url, request)

        try:
            response = await client.post(
                credentials.scrape_endpoint,
                json=body,
                headers=_firecrawl_headers(read_secret(credentials.api_key)),
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            return crawl_upstream_error(
                url,
                f"Firecrawl scrape timed out after {timeout}s",
                raw=transport_error_raw(exc),
            )
        except httpx.HTTPError as exc:
            return crawl_upstream_error(
                url,
                f"Firecrawl scrape request failed: {exc}",
                raw=transport_error_raw(exc),
            )

        if response.status_code >= 400:
            return crawl_upstream_error(
                url,
                upstream_error_message(
                    response,
                    provider_label=f"{_FIRECRAWL_PROVIDER_LABEL} scrape",
                ),
                raw=upstream_response_raw(response),
            )

        try:
            payload = response.json()
        except ValueError as exc:
            return crawl_upstream_error(
                url,
                f"Firecrawl scrape returned invalid JSON: {exc}",
                raw=upstream_response_raw(response),
            )

        if not isinstance(payload, dict):
            return crawl_upstream_error(
                url,
                "Firecrawl scrape returned unexpected response shape",
                raw=payload,
            )

        return _map_single_scrape_result(url, payload)

    async def _batch_scrape_urls(
        self,
        client: httpx.AsyncClient,
        *,
        urls: list[str],
        request: FirecrawlCrawlRequest,  # type: ignore[valid-type]
        timeout: int,
        deadline: float,
    ) -> list[CrawlUrlResult]:
        body = build_firecrawl_batch_scrape_body(urls, request)

        try:
            start_response = await client.post(
                credentials.batch_scrape_endpoint,
                json=body,
                headers=_firecrawl_headers(read_secret(credentials.api_key)),
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise_batch_upstream_failure(
                f"Firecrawl batch scrape timed out after {timeout}s",
                raw=transport_error_raw(exc),
            )
        except httpx.HTTPError as exc:
            raise_batch_upstream_failure(
                f"Firecrawl batch scrape request failed: {exc}",
                raw=transport_error_raw(exc),
            )

        if start_response.status_code >= 400:
            raise_batch_upstream_failure(
                upstream_error_message(
                    start_response,
                    provider_label=f"{_FIRECRAWL_PROVIDER_LABEL} batch scrape",
                ),
                raw=upstream_response_raw(start_response),
            )

        try:
            start_payload = start_response.json()
        except ValueError as exc:
            raise_batch_upstream_failure(
                f"Firecrawl batch scrape returned invalid JSON: {exc}",
                raw=upstream_response_raw(start_response),
            )

        if not isinstance(start_payload, dict):
            raise_batch_upstream_failure(
                "Firecrawl batch scrape returned unexpected response shape",
                raw=start_payload,
            )

        status_url = _resolve_batch_scrape_status_url(
            start_payload,
            batch_scrape_endpoint=credentials.batch_scrape_endpoint,
        )
        if status_url is None:
            raise_batch_upstream_failure(
                "Firecrawl batch scrape response missing job id",
                raw=start_payload,
            )

        try:
            final_payload = await poll_batch_scrape(
                client,
                status_url=status_url,
                api_key=read_secret(credentials.api_key),
                deadline=deadline,
            )
        except TimeoutError as exc:
            raise_batch_upstream_failure(
                f"Firecrawl batch scrape timed out after {timeout}s",
                raw=transport_error_raw(exc),
            )
        except httpx.HTTPError as exc:
            raise_batch_upstream_failure(
                f"Firecrawl batch scrape polling failed: {exc}",
                raw=transport_error_raw(exc),
            )

        return _map_firecrawl_batch_results(urls, final_payload)


def _resolve_batch_scrape_status_url(
    start_payload: dict[str, Any],
    *,
    batch_scrape_endpoint: str,
) -> str | None:
    url = start_payload.get("url")
    if isinstance(url, str) and url:
        return url

    job_id = start_payload.get("id")
    if isinstance(job_id, str) and job_id:
        return join_url_path(batch_scrape_endpoint, job_id)

    return None


def _map_single_scrape_result(url: str, payload: dict[str, Any]) -> CrawlUrlResult:
    success = payload.get("success")
    if success is False:
        detail = payload.get("error") or payload.get("message")
        message = detail if isinstance(detail, str) else "Firecrawl scrape failed"
        return crawl_upstream_error(url, message, raw=payload)

    data = payload.get("data")
    if not isinstance(data, dict):
        return crawl_upstream_error(
            url,
            "Firecrawl scrape returned unexpected data shape",
            raw=payload,
        )

    markdown = data.get("markdown")
    if isinstance(markdown, str) and markdown:
        return CrawlUrlResult(
            url=url,
            content=markdown,
            content_type="text/markdown",
            raw=data,
        )

    return crawl_upstream_error(
        url,
        "Firecrawl returned no markdown for URL",
        raw=payload,
    )


def _map_firecrawl_batch_results(
    urls: list[str],
    payload: dict[str, Any],
) -> list[CrawlUrlResult]:
    status = payload.get("status")
    if status == "failed":
        raise_batch_upstream_failure(
            "Firecrawl batch scrape job failed",
            raw=payload,
        )

    data = payload.get("data", [])
    if not isinstance(data, list):
        raise_batch_upstream_failure(
            "Firecrawl batch scrape returned unexpected data shape",
            raw=payload,
        )

    by_url: dict[str, CrawlUrlResult] = {}
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        item_url = item.get("url") or item.get("sourceURL") or item.get("source_url")
        target_url = item_url if isinstance(item_url, str) else None
        if target_url is None and index < len(urls):
            target_url = urls[index]
        if target_url is None:
            continue

        markdown = item.get("markdown")
        if isinstance(markdown, str) and markdown:
            by_url[target_url] = CrawlUrlResult(
                url=target_url,
                content=markdown,
                content_type="text/markdown",
                raw=item,
            )
        else:
            by_url[target_url] = crawl_upstream_error(
                target_url,
                "Firecrawl returned no markdown for URL",
                raw=item,
            )

    results: list[CrawlUrlResult] = []
    for url in urls:
        if url in by_url:
            results.append(by_url[url])
        else:
            results.append(
                crawl_upstream_error(
                    url,
                    "URL not found in Firecrawl response",
                    raw=payload,
                ),
            )
    return results
