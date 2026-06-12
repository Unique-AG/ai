from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from unique_search_proxy_core.crawlers.base import BaseCrawler, CrawlerType
from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest
from unique_search_proxy_core.schema import (
    CrawlUrlResult,
    PerUrlError,
    ProxyErrorCode,
)

from unique_search_proxy_client.web.core.crawlers.tavily.request_body import (
    build_tavily_extract_body,
)
from unique_search_proxy_client.web.settings.providers.tavily import (
    tavily_crawl_credentials as credentials,
)

_LOGGER = logging.getLogger(__name__)

_TAVILY_BATCH_SIZE = 20


def _tavily_headers(api_key: str) -> dict[str, str]:
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


def _map_batch_response(
    batch_urls: list[str],
    payload: dict[str, Any],
) -> dict[str, CrawlUrlResult]:
    by_url: dict[str, CrawlUrlResult] = {}

    for item in payload.get("results", []):
        url = item.get("url")
        if not isinstance(url, str):
            continue
        raw_content = item.get("raw_content")
        content = raw_content if isinstance(raw_content, str) else None
        by_url[url] = CrawlUrlResult(
            url=url,
            content=content,
            content_type="text/markdown",
            raw=item,
        )

    for item in payload.get("failed_results", []):
        url = item.get("url")
        if not isinstance(url, str):
            continue
        error_message = item.get("error", "Tavily extract failed")
        if not isinstance(error_message, str):
            error_message = str(error_message)
        by_url[url] = _error_result(url, error_message)

    for url in batch_urls:
        if url not in by_url:
            by_url[url] = _error_result(url, "URL not found in Tavily response")

    return by_url


class TavilyCrawlerService(BaseCrawler[TavilyCrawlRequest]):
    """Tavily Extract API crawler (httpx, batched POST /extract)."""

    crawler_id = CrawlerType.TAVILY.value

    async def crawl(self, request: TavilyCrawlRequest) -> list[CrawlUrlResult]:  # type: ignore[override]
        credentials.check_credentials()

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Tavily crawler")

        urls = list(request.urls)
        timeout = min(max(request.timeout, 1), 60)
        batches = [
            urls[index : index + _TAVILY_BATCH_SIZE]
            for index in range(0, len(urls), _TAVILY_BATCH_SIZE)
        ]

        batch_results = await asyncio.gather(
            *[
                self._extract_batch(
                    client,
                    batch,
                    request,
                    timeout=timeout,
                )
                for batch in batches
            ],
        )

        by_url: dict[str, CrawlUrlResult] = {}
        for batch, mapped in zip(batches, batch_results, strict=True):
            by_url.update(mapped)
            for url in batch:
                if url not in mapped:
                    by_url[url] = _error_result(url, "URL not found in Tavily response")

        return [by_url[url] for url in urls]

    async def _extract_batch(
        self,
        client: httpx.AsyncClient,
        batch_urls: list[str],
        request: TavilyCrawlRequest,
        *,
        timeout: float,
    ) -> dict[str, CrawlUrlResult]:
        body = build_tavily_extract_body(batch_urls, request)
        try:
            response = await client.post(
                credentials.extract_endpoint,
                json=body,
                headers=_tavily_headers(credentials.api_key),
                timeout=timeout,
            )
        except httpx.TimeoutException:
            message = f"Tavily extract timed out after {timeout}s"
            return {url: _error_result(url, message) for url in batch_urls}
        except httpx.HTTPError as exc:
            message = f"Tavily extract request failed: {exc}"
            return {url: _error_result(url, message) for url in batch_urls}

        if response.status_code >= 400:
            message = _upstream_error_message(response)
            return {url: _error_result(url, message) for url in batch_urls}

        try:
            payload = response.json()
        except ValueError as exc:
            message = f"Tavily extract returned invalid JSON: {exc}"
            return {url: _error_result(url, message) for url in batch_urls}

        if not isinstance(payload, dict):
            message = "Tavily extract returned unexpected response shape"
            return {url: _error_result(url, message) for url in batch_urls}

        return _map_batch_response(batch_urls, payload)


def _upstream_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Tavily extract failed with HTTP {response.status_code}"

    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload.get("message")
        if isinstance(detail, str) and detail:
            return detail

    return f"Tavily extract failed with HTTP {response.status_code}"
