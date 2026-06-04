from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from httpx import AsyncClient, Timeout
from unique_search_proxy_core.crawlers.base import BaseCrawler, CrawlerType
from unique_search_proxy_core.crawlers.basic.processing.policy import (
    ContentTypeHandlerPolicy,
)
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlerRequest
from unique_search_proxy_core.schema import (
    CrawlUrlResult,
    PerUrlError,
    ProxyErrorCode,
)

from unique_search_proxy_client.web.core.crawlers.basic.processing import (
    ContentProcessingError,
    ContentProcessingTimeoutError,
    process_content,
)
from unique_search_proxy_client.web.core.crawlers.basic.user_agent import (
    random_user_agent,
)

_LOGGER = logging.getLogger(__name__)


def _content_type_from_response(response: httpx.Response) -> str | None:
    header = response.headers.get("content-type")
    if header is None:
        return None
    return str(header).split(";")[0].strip().lower() or None


class BasicCrawlerService(BaseCrawler[BasicCrawlerRequest]):
    """Fetch URLs over HTTP and return the response body plus content type."""

    crawler_id = CrawlerType.BASIC.value

    async def crawl(self, request: BasicCrawlerRequest) -> list[CrawlUrlResult]:  # type: ignore
        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Basic crawler")

        timeout = request.timeout
        semaphore = asyncio.Semaphore(request.max_concurrent_requests)
        return list(
            await asyncio.gather(
                *[
                    self._crawl_one(
                        client,
                        url,
                        timeout=timeout,
                        semaphore=semaphore,
                        content_type_handlers=request.content_types.to_handlers(),
                    )
                    for url in request.urls
                ],
            ),
        )

    async def _crawl_one(
        self,
        client: AsyncClient,
        url: str,
        *,
        timeout: int,
        semaphore: asyncio.Semaphore,
        content_type_handlers: dict[str, ContentTypeHandlerPolicy],
    ) -> CrawlUrlResult:
        request_url = url.strip()
        async with semaphore:
            headers = {"User-Agent": random_user_agent()}
            try:
                response = await client.get(
                    request_url,
                    headers=headers,
                    timeout=Timeout(timeout),
                    follow_redirects=True,
                )
            except httpx.TimeoutException as exc:
                _LOGGER.warning("Basic crawl timed out for %s: %s", request_url, exc)
                return CrawlUrlResult(
                    url=request_url,
                    content=None,
                    raw=None,
                    content_type=None,
                    error=PerUrlError(
                        code=ProxyErrorCode.UPSTREAM_TIMEOUT.value,
                        message=f"Crawl timed out after {timeout}s",
                    ),
                )
            except httpx.HTTPError as exc:
                _LOGGER.warning("Basic crawl failed for %s: %s", request_url, exc)
                return CrawlUrlResult(
                    url=request_url,
                    content=None,
                    raw=None,
                    content_type=None,
                    error=PerUrlError(
                        code=ProxyErrorCode.UPSTREAM_ERROR.value,
                        message=str(exc),
                    ),
                )

            content_type = _content_type_from_response(response)
            raw_body = response.text
            if response.is_error:
                _LOGGER.warning(
                    "Basic crawl HTTP error for %s: %s",
                    request_url,
                    response.status_code,
                )
                return CrawlUrlResult(
                    url=request_url,
                    content=None,
                    raw=raw_body,
                    content_type=content_type,
                    error=PerUrlError(
                        code=ProxyErrorCode.UPSTREAM_ERROR.value,
                        message=f"HTTP {response.status_code} while fetching URL",
                    ),
                )

            content = await self._maybe_process_content(
                raw_body,
                content_type,
                request_url=request_url,
                timeout=timeout,
                content_type_handlers=content_type_handlers,
            )
            if isinstance(content, CrawlUrlResult):
                return content

            return CrawlUrlResult(
                url=request_url,
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
            return CrawlUrlResult(
                url=request_url,
                content=None,
                raw=raw_body,
                content_type=content_type,
                error=PerUrlError(
                    code=ProxyErrorCode.UPSTREAM_TIMEOUT.value,
                    message=str(exc),
                ),
            )
        except ContentProcessingError as exc:
            _LOGGER.warning(
                "Basic crawl processing failed for %s: %s",
                request_url,
                exc,
            )
            return CrawlUrlResult(
                url=request_url,
                content=None,
                raw=raw_body,
                content_type=content_type,
                error=PerUrlError(
                    code=ProxyErrorCode.UPSTREAM_ERROR.value,
                    message=str(exc),
                ),
            )

    @staticmethod
    def llm_call_schema(config: Any) -> type[Any]:
        from unique_search_proxy_core.crawlers.basic.schema import (
            BasicCrawlerCall,
            BasicCrawlerConfig,
        )
        from unique_search_proxy_core.projection import project_call_schema

        if not isinstance(config, BasicCrawlerConfig):
            config = BasicCrawlerConfig.model_validate(config)
        return project_call_schema(BasicCrawlerCall, ["urls"])
