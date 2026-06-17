from __future__ import annotations

import asyncio
import logging

import httpx
from httpx import AsyncClient, Timeout
from unique_search_proxy_core.crawlers.base import BaseCrawler, CrawlerType
from unique_search_proxy_core.crawlers.basic.processing.policy import (
    ContentTypeHandlerPolicy,
)
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlRequest
from unique_search_proxy_core.schema import (
    CrawlUrlResult,
    ProxyErrorCode,
)
from unique_search_proxy_core.url_safety import (
    ResolvedCrawlTarget,
    bypass_crawl_target,
    pinned_httpx_get_args,
)

from unique_search_proxy_client.web.core.crawlers.basic.processing import (
    ContentProcessingError,
    ContentProcessingTimeoutError,
    process_content,
)
from unique_search_proxy_client.web.core.crawlers.basic.user_agent import (
    random_user_agent,
)
from unique_search_proxy_client.web.core.provider_response import (
    crawl_upstream_error,
    transport_error_raw,
)
from unique_search_proxy_client.web.core.url_safety.gate import AllowedCrawlTarget

_LOGGER = logging.getLogger(__name__)


def _content_type_from_response(response: httpx.Response) -> str | None:
    header = response.headers.get("content-type")
    if header is None:
        return None
    return str(header).split(";")[0].strip().lower() or None


class BasicCrawlerService(BaseCrawler[BasicCrawlRequest]):
    """Fetch URLs over HTTP and return the response body plus content type."""

    crawler_id = CrawlerType.BASIC.value

    async def crawl(self, request: BasicCrawlRequest) -> list[CrawlUrlResult]:  # type: ignore[override]
        bypass_targets = [
            AllowedCrawlTarget(
                display_url=url.strip(),
                resolved=bypass_crawl_target(url),
            )
            for url in request.urls
        ]
        return await self.crawl_pinned(request, bypass_targets)

    async def crawl_pinned(
        self,
        request: BasicCrawlRequest, # type: ignore[valid-type]
        allowed_targets: list[AllowedCrawlTarget],
    ) -> list[CrawlUrlResult]:
        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Basic crawler")

        display_urls = list(request.urls)
        if len(allowed_targets) != len(display_urls):
            msg = "allowed_targets length must match request.urls length"
            raise ValueError(msg)

        timeout = request.timeout
        semaphore = asyncio.Semaphore(request.max_concurrent_requests)
        return list(
            await asyncio.gather(
                *[
                    self._crawl_one(
                        client,
                        allowed_target.display_url,
                        resolved_target=allowed_target.resolved,
                        timeout=timeout,
                        semaphore=semaphore,
                        content_type_handlers=request.content_types.to_handlers(),
                    )
                    for allowed_target in allowed_targets
                ],
            ),
        )

    async def _crawl_one(
        self,
        client: AsyncClient,
        display_url: str,
        *,
        resolved_target: ResolvedCrawlTarget,
        timeout: int,
        semaphore: asyncio.Semaphore,
        content_type_handlers: dict[str, ContentTypeHandlerPolicy],
    ) -> CrawlUrlResult:
        request_url, pin_headers, extensions = pinned_httpx_get_args(resolved_target)
        async with semaphore:
            headers = {"User-Agent": random_user_agent(), **pin_headers}

            try:
                response = await client.get(
                    request_url,
                    headers=headers,
                    extensions=extensions or None,
                    timeout=Timeout(timeout),
                    follow_redirects=True,
                )
            except httpx.TimeoutException as exc:
                _LOGGER.warning("Basic crawl timed out for %s: %s", display_url, exc)
                return crawl_upstream_error(
                    display_url,
                    f"Crawl timed out after {timeout}s",
                    content_type=None,
                    code=ProxyErrorCode.UPSTREAM_TIMEOUT.value,
                    raw=transport_error_raw(exc),
                )
            except httpx.HTTPError as exc:
                _LOGGER.warning("Basic crawl failed for %s: %s", display_url, exc)
                return crawl_upstream_error(
                    display_url,
                    str(exc),
                    content_type=None,
                    raw=transport_error_raw(exc),
                )

            content_type = _content_type_from_response(response)
            raw_body = response.text
            if response.is_error:
                _LOGGER.warning(
                    "Basic crawl HTTP error for %s: %s",
                    display_url,
                    response.status_code,
                )
                return crawl_upstream_error(
                    display_url,
                    f"HTTP {response.status_code} while fetching URL",
                    content_type=content_type,
                    raw=raw_body,
                )

            content = await self._maybe_process_content(
                raw_body,
                content_type,
                request_url=display_url,
                timeout=timeout,
                content_type_handlers=content_type_handlers,
            )
            if isinstance(content, CrawlUrlResult):
                return content

            return CrawlUrlResult(
                url=display_url,
                content=content,
                raw=raw_body,
                content_type=content_type,
                error=None,
            )

    async def _maybe_process_content(
        self,
        raw_body: str,
        content_type: str | None,
        *,
        request_url: str,
        timeout: int,
        content_type_handlers: dict[str, ContentTypeHandlerPolicy],
    ) -> str | None | CrawlUrlResult:
        if not content_type_handlers:
            return None

        try:
            return await process_content(
                raw_body,
                content_type,
                handlers=content_type_handlers,
                timeout=float(timeout),
            )
        except ContentProcessingTimeoutError as exc:
            _LOGGER.warning(
                "Basic crawl processing timed out for %s: %s",
                request_url,
                exc,
            )
            return crawl_upstream_error(
                request_url,
                str(exc),
                content_type=content_type,
                code=ProxyErrorCode.UPSTREAM_TIMEOUT.value,
                raw=raw_body,
            )
        except ContentProcessingError as exc:
            _LOGGER.warning(
                "Basic crawl processing failed for %s: %s",
                request_url,
                exc,
            )
            return crawl_upstream_error(
                request_url,
                str(exc),
                content_type=content_type,
                raw=raw_body,
            )
