from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict
from unique_search_proxy_core.crawlers.base import BaseCrawler, CrawlerType
from unique_search_proxy_core.crawlers.jina.schema import JinaCrawlRequest
from unique_search_proxy_core.schema import CrawlUrlResult

from unique_search_proxy_client.web.core.crawlers.jina.request_body import (
    build_jina_reader_body,
)
from unique_search_proxy_client.web.core.provider_response import (
    crawl_upstream_error,
    transport_error_raw,
    upstream_response_raw,
)
from unique_search_proxy_client.web.settings.providers.jina import (
    jina_crawl_credentials as credentials,
)

_LOGGER = logging.getLogger(__name__)


class _ReaderData(BaseModel):
    title: str | None = None
    description: str | None = None
    url: str | None = None
    content: str | None = None


class _ReaderResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: int
    status: int | str | None = None
    message: str | None = None
    data: _ReaderData | None = None


def _jina_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _jina_reader_error_message(payload: dict[str, Any], code: int) -> str:
    detail = payload.get("message") or payload.get("error")
    if isinstance(detail, str) and detail.strip():
        return f"Jina reader error ({code}): {detail}"
    return f"Jina reader error code {code}"


class JinaCrawlerService(BaseCrawler[JinaCrawlRequest]):
    """Jina Reader API crawler (httpx POST per URL)."""

    crawler_id = CrawlerType.JINA.value

    async def crawl(self, request: JinaCrawlRequest) -> list[CrawlUrlResult]:  # type: ignore[override]
        credentials.check_credentials()

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Jina crawler")

        urls = list(request.urls)
        timeout = request.timeout
        headers = _jina_headers(credentials.api_key)
        semaphore = asyncio.Semaphore(request.max_concurrent_requests)

        async def crawl_one(url: str) -> CrawlUrlResult:
            async with semaphore:
                return await self._crawl_url(
                    client,
                    url,
                    request=request,
                    headers=headers,
                    timeout=timeout,
                )

        return list(await asyncio.gather(*(crawl_one(url) for url in urls)))

    async def _crawl_url(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        request: JinaCrawlRequest,
        headers: dict[str, str],
        timeout: float,
    ) -> CrawlUrlResult:
        body = build_jina_reader_body(url, request)
        try:
            response = await client.post(
                credentials.reader_endpoint,
                headers=headers,
                json=body,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            return crawl_upstream_error(
                url,
                f"Jina reader timed out after {timeout}s",
                raw=transport_error_raw(exc),
            )
        except httpx.HTTPError as exc:
            return crawl_upstream_error(
                url,
                f"Jina reader request failed: {exc}",
                raw=transport_error_raw(exc),
            )

        raw = upstream_response_raw(response)

        if not isinstance(raw, dict):
            return crawl_upstream_error(
                url,
                "Jina reader returned unexpected response shape",
                raw=raw,
            )

        payload: dict[str, Any] = raw

        try:
            reader_response = _ReaderResponse.model_validate(payload)
        except ValueError as exc:
            return crawl_upstream_error(
                url,
                f"Jina reader returned unexpected shape: {exc}",
                raw=payload,
            )

        if reader_response.code != 200:
            message = _jina_reader_error_message(payload, reader_response.code)
            _LOGGER.warning(
                "Jina reader failure url=%s endpoint=%s http_status=%s code=%s",
                url,
                credentials.reader_endpoint,
                response.status_code,
                reader_response.code,
            )
            return crawl_upstream_error(url, message, raw=payload)

        content = reader_response.data.content if reader_response.data else None
        if not content:
            return crawl_upstream_error(
                url,
                "Jina reader returned empty content",
                raw=payload,
            )

        return CrawlUrlResult(
            url=url,
            content=content,
            content_type="text/markdown",
            raw=payload,
        )
