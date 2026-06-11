"""HTTP client for ``POST /v1/crawl``."""

from __future__ import annotations

from typing import Any, Literal, cast, overload

from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request

from unique_search_proxy_sdk._generated.api.crawl import crawl_v1_crawl_post
from unique_search_proxy_sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy_sdk._http import unwrap_response
from unique_search_proxy_sdk._transport import OpenapiTransport
from unique_search_proxy_sdk.converters import to_sdk_crawl_request


class CrawlClient:
    """Crawl URLs via flat, crawler-specific request bodies."""

    def __init__(self, transport: OpenapiTransport) -> None:
        self._transport = transport

    @overload
    async def crawl(
        self,
        urls: list[str],
        *,
        crawler: Literal[CrawlerType.BASIC] = CrawlerType.BASIC,
        timeout: int = ...,
        content_types: ContentTypeToggles | None = ...,
        max_concurrent_requests: int = ...,
        exposed_fields: list[str] | None = ...,
    ) -> CrawlResponse: ...

    @overload
    async def crawl(
        self,
        urls: list[str],
        *,
        crawler: CrawlerType | str,
        **params: Any,
    ) -> CrawlResponse: ...

    async def crawl(
        self,
        urls: list[str],
        *,
        crawler: CrawlerType | str = CrawlerType.BASIC,
        content_types: ContentTypeToggles | None = None,
        **params: Any,
    ) -> CrawlResponse:
        """Crawl URLs with a flat body validated by core request models."""
        crawler_value = (
            crawler.value if isinstance(crawler, CrawlerType) else crawler
        )
        payload: dict[str, Any] = {"urls": urls, "crawler": crawler_value, **params}
        if content_types is not None:
            payload["contentTypes"] = content_types.model_dump(
                mode="json",
                by_alias=True,
            )
        validated = parse_crawl_request(payload)
        sdk_body = to_sdk_crawl_request(validated)
        response = await crawl_v1_crawl_post.asyncio_detailed(
            client=self._transport.openapi,
            body=sdk_body,
        )
        return cast(CrawlResponse, unwrap_response(response))


__all__ = ["CrawlClient"]
