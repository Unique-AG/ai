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
from unique_search_proxy_core.errors import ResponseTooLargeError
from unique_search_proxy_core.http_client import read_capped_body
from unique_search_proxy_core.schema import (
    CrawlUrlResult,
    ProxyErrorCode,
)
from unique_search_proxy_core.url_safety import (
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
    bypass_crawl_target,
    safe_pinned_httpx_stream,
    url_safety_settings,
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
    crawl_forbidden_target,
    crawl_upstream_error,
    transport_error_raw,
)
from unique_search_proxy_client.web.core.url_safety.gate import AllowedCrawlTarget
from unique_search_proxy_client.web.monitoring.metrics import record_crawl_blocked
from unique_search_proxy_client.web.settings.client import http_client_settings

_LOGGER = logging.getLogger(__name__)

# Only encodings whose decoded size read_capped_body can bound in small steps;
# brotli and zstd reach far higher compression ratios.
_ACCEPT_ENCODING = "gzip, deflate"
_SUPPORTED_CONTENT_ENCODINGS = frozenset({"gzip", "deflate", "identity"})


def _content_type_from_response(response: httpx.Response) -> str | None:
    header = response.headers.get("content-type")
    if header is None:
        return None
    return str(header).split(";")[0].strip().lower() or None


def _unsupported_content_encoding(response: httpx.Response) -> str | None:
    header = response.headers.get("content-encoding", "")
    for encoding in header.split(","):
        normalized = encoding.strip().lower()
        if normalized and normalized not in _SUPPORTED_CONTENT_ENCODINGS:
            return normalized
    return None


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
        request: BasicCrawlRequest,  # type: ignore[valid-type]
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
        async with semaphore:
            try:
                async with safe_pinned_httpx_stream(
                    client,
                    resolved_target,
                    headers={
                        "User-Agent": random_user_agent(),
                        "Accept-Encoding": _ACCEPT_ENCODING,
                    },
                    timeout=Timeout(timeout),
                    max_redirect_hops=url_safety_settings.max_redirect_hops,
                    enforce_url_safety=url_safety_settings.enabled,
                ) as response:
                    content_type = _content_type_from_response(response)
                    unsupported_encoding = _unsupported_content_encoding(response)
                    if unsupported_encoding is not None:
                        _LOGGER.warning(
                            "Basic crawl rejected content encoding %s",
                            unsupported_encoding,
                        )
                        return crawl_upstream_error(
                            display_url,
                            f"Unsupported content encoding: {unsupported_encoding}",
                            content_type=content_type,
                            status_code=response.status_code,
                        )
                    body = await read_capped_body(
                        response,
                        max_bytes=http_client_settings.max_response_bytes,
                    )
                    raw_body = body.decode(
                        response.encoding or "utf-8",
                        errors="replace",
                    )
            except CrawlTargetValidationError as exc:
                blocked = exc.blocked_targets[0]
                record_crawl_blocked(blocked.category)
                _LOGGER.warning(
                    "Basic crawl blocked redirect: %s",
                    blocked.category,
                )
                return crawl_forbidden_target(display_url, blocked.reason)
            except ResponseTooLargeError as exc:
                _LOGGER.warning("Basic crawl response too large: %s", exc.message)
                return crawl_upstream_error(
                    display_url,
                    exc.message,
                    content_type=None,
                    code=ProxyErrorCode.RESPONSE_TOO_LARGE.value,
                )
            except httpx.TimeoutException as exc:
                _LOGGER.warning(
                    "Basic crawl timed out error_type=%s",
                    type(exc).__name__,
                )
                return crawl_upstream_error(
                    display_url,
                    f"Crawl timed out after {timeout}s",
                    content_type=None,
                    code=ProxyErrorCode.UPSTREAM_TIMEOUT.value,
                    raw=transport_error_raw(exc),
                )
            except httpx.HTTPError as exc:
                _LOGGER.warning(
                    "Basic crawl failed error_type=%s",
                    type(exc).__name__,
                )
                return crawl_upstream_error(
                    display_url,
                    str(exc),
                    content_type=None,
                    raw=transport_error_raw(exc),
                )

            if response.is_error:
                _LOGGER.warning(
                    "Basic crawl HTTP error http_status=%s",
                    response.status_code,
                )
                return crawl_upstream_error(
                    display_url,
                    f"HTTP {response.status_code} while fetching URL",
                    content_type=content_type,
                    raw=raw_body,
                    status_code=response.status_code,
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
            _LOGGER.warning("Basic crawl processing timed out: %s", exc)
            return crawl_upstream_error(
                request_url,
                str(exc),
                content_type=content_type,
                code=ProxyErrorCode.UPSTREAM_TIMEOUT.value,
                raw=raw_body,
            )
        except ContentProcessingError as exc:
            _LOGGER.warning(
                "Basic crawl processing failed error_type=%s",
                type(exc.__cause__ or exc).__name__,
            )
            return crawl_upstream_error(
                request_url,
                str(exc),
                content_type=content_type,
                raw=raw_body,
            )
