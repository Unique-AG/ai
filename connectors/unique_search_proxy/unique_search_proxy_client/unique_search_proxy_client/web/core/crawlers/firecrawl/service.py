from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from unique_search_proxy_core.crawlers.base import BaseCrawler, CrawlerType
from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlCrawlRequest,
)
from unique_search_proxy_core.schema import (
    CrawlUrlResult,
    PerUrlError,
    ProxyErrorCode,
)

from unique_search_proxy_client.web.core.crawlers.firecrawl.polling import (
    poll_batch_scrape,
)
from unique_search_proxy_client.web.core.crawlers.firecrawl.request_body import (
    build_firecrawl_batch_scrape_body,
    build_firecrawl_scrape_body,
)
from unique_search_proxy_client.web.settings.providers.firecrawl import (
    firecrawl_crawl_credentials as credentials,
)
from unique_search_proxy_client.web.utils.url import join_url_path

_LOGGER = logging.getLogger(__name__)


def _firecrawl_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _error_result(url: str, message: str) -> CrawlUrlResult:
    return CrawlUrlResult(
        url=url,
        content=None,
        content_type="text/markdown",
        error=PerUrlError(
            code=ProxyErrorCode.UPSTREAM_ERROR.value,
            message=message,
        ),
    )


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
        request: FirecrawlCrawlRequest,
        timeout: int,
    ) -> CrawlUrlResult:
        body = build_firecrawl_scrape_body(url, request)

        try:
            response = await client.post(
                credentials.scrape_endpoint,
                json=body,
                headers=_firecrawl_headers(credentials.api_key),
                timeout=timeout,
            )
        except httpx.TimeoutException:
            return _error_result(url, f"Firecrawl scrape timed out after {timeout}s")
        except httpx.HTTPError as exc:
            return _error_result(url, f"Firecrawl scrape request failed: {exc}")

        if response.status_code >= 400:
            return _error_result(
                url, _upstream_error_message(response, operation="scrape")
            )

        try:
            payload = response.json()
        except ValueError as exc:
            return _error_result(
                url,
                f"Firecrawl scrape returned invalid JSON: {exc}",
            )

        return _map_single_scrape_result(url, payload)

    async def _batch_scrape_urls(
        self,
        client: httpx.AsyncClient,
        *,
        urls: list[str],
        request: FirecrawlCrawlRequest,
        timeout: int,
        deadline: float,
    ) -> list[CrawlUrlResult]:
        body = build_firecrawl_batch_scrape_body(urls, request)

        try:
            start_response = await client.post(
                credentials.batch_scrape_endpoint,
                json=body,
                headers=_firecrawl_headers(credentials.api_key),
                timeout=timeout,
            )
        except httpx.TimeoutException:
            message = f"Firecrawl batch scrape timed out after {timeout}s"
            return [_error_result(url, message) for url in urls]
        except httpx.HTTPError as exc:
            message = f"Firecrawl batch scrape request failed: {exc}"
            return [_error_result(url, message) for url in urls]

        if start_response.status_code >= 400:
            message = _upstream_error_message(
                start_response,
                operation="batch scrape",
            )
            return [_error_result(url, message) for url in urls]

        try:
            start_payload = start_response.json()
        except ValueError as exc:
            message = f"Firecrawl batch scrape returned invalid JSON: {exc}"
            return [_error_result(url, message) for url in urls]

        if not isinstance(start_payload, dict):
            message = "Firecrawl batch scrape returned unexpected response shape"
            return [_error_result(url, message) for url in urls]

        status_url = _resolve_batch_scrape_status_url(
            start_payload,
            batch_scrape_endpoint=credentials.batch_scrape_endpoint,
        )
        if status_url is None:
            message = "Firecrawl batch scrape response missing job id"
            return [_error_result(url, message) for url in urls]

        try:
            final_payload = await poll_batch_scrape(
                client,
                status_url=status_url,
                api_key=credentials.api_key,
                deadline=deadline,
            )
        except TimeoutError:
            message = f"Firecrawl batch scrape timed out after {timeout}s"
            return [_error_result(url, message) for url in urls]
        except httpx.HTTPError as exc:
            message = f"Firecrawl batch scrape polling failed: {exc}"
            return [_error_result(url, message) for url in urls]

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
        return _error_result(url, message)

    data = payload.get("data")
    if not isinstance(data, dict):
        return _error_result(url, "Firecrawl scrape returned unexpected data shape")

    markdown = data.get("markdown")
    if isinstance(markdown, str) and markdown:
        return CrawlUrlResult(
            url=url,
            content=markdown,
            content_type="text/markdown",
            raw=data,
        )

    return _error_result(url, "Firecrawl returned no markdown for URL")


def _map_firecrawl_batch_results(
    urls: list[str],
    payload: dict[str, Any],
) -> list[CrawlUrlResult]:
    status = payload.get("status")
    if status == "failed":
        message = "Firecrawl batch scrape job failed"
        return [_error_result(url, message) for url in urls]

    data = payload.get("data", [])
    if not isinstance(data, list):
        message = "Firecrawl batch scrape returned unexpected data shape"
        return [_error_result(url, message) for url in urls]

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
            by_url[target_url] = _error_result(
                target_url,
                "Firecrawl returned no markdown for URL",
            )

    results: list[CrawlUrlResult] = []
    for url in urls:
        if url in by_url:
            results.append(by_url[url])
        else:
            results.append(_error_result(url, "URL not found in Firecrawl response"))
    return results


def _upstream_error_message(
    response: httpx.Response,
    *,
    operation: str,
) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Firecrawl {operation} failed with HTTP {response.status_code}"

    if isinstance(payload, dict):
        detail = payload.get("error") or payload.get("message")
        if isinstance(detail, str) and detail:
            return detail

    return f"Firecrawl {operation} failed with HTTP {response.status_code}"
