import asyncio
import logging
import re
from typing import Literal

import timeout_decorator
from httpx import AsyncClient, Timeout
from markdownify import markdownify
from pydantic import Field
from typing_extensions import override

from unique_web_search.services.client.proxy_config import async_client
from unique_web_search.services.crawlers.base import (
    BaseCrawler,
    BaseCrawlerConfig,
    CrawlerType,
)
from unique_web_search.services.crawlers.utils import get_random_user_agent
from unique_web_search.services.url_safety import (
    CrawlTargetValidationError,
    resolve_crawl_target,
)

_LOGGER = logging.getLogger(__name__)

unwanted_types = {
    "application/octet-stream",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/",
    "video/",
    "audio/",
}


class BasicCrawlerConfig(BaseCrawlerConfig[CrawlerType.BASIC]):
    crawler_type: Literal[CrawlerType.BASIC] = CrawlerType.BASIC
    url_pattern_blacklist: list[str] = Field(
        default=[r".*\.pdf$"],
        description="List of URL patterns to blacklist",
    )
    unwanted_content_types: set[str] = Field(
        default=unwanted_types,
        description="Set of content types to not allow",
    )
    max_concurrent_requests: int = Field(
        default=10,
        description="The maximum number of concurrent requests to make to the same domain.",
    )


class BasicCrawler(BaseCrawler[BasicCrawlerConfig]):
    def __init__(self, config: BasicCrawlerConfig):
        super().__init__(config)

        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(
            self.config.max_concurrent_requests
        )

    # TODO: Find a good way for tracking
    # @track(
    #     tags=["basic", "scrape"],
    # )
    @override
    async def _crawl(self, urls: list[str]) -> list[str]:
        async with async_client(timeout=Timeout(self.config.timeout)) as client:
            tasks = [self._crawl_url_with_client(client, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            validation_errors = [
                result
                for result in results
                if isinstance(result, CrawlTargetValidationError)
            ]
            if validation_errors:
                raise validation_errors[0]

            markdowns: list[str] = []
            for result in results:
                if isinstance(result, BaseException):
                    markdowns.append(
                        f"Unexpected error occurred while crawling the URL: {result}"
                    )

                else:
                    markdowns.append(result)

            return markdowns

    async def _crawl_url_with_client(self, client: AsyncClient, url: str) -> str:
        headers = {"User-Agent": get_random_user_agent()}

        if self._is_url_blacklisted(url):
            return "Unable to crawl URL due to blacklisted pattern"

        request_url, request_headers, request_extensions = self._build_request_target(
            url, headers
        )
        response = await client.get(
            request_url,
            headers=request_headers,
            extensions=request_extensions or None,
        )

        _ = response.raise_for_status()

        content_type = (
            str(response.headers.get("content-type", "")).lower().split(";")[0]
        )

        if self._content_type_not_allowed(content_type):
            return f"Content type {content_type} is not allowed"

        content = response.text

        markdown = _markdownify_html_with_timeout(content, self.config.timeout)

        return markdown

    def _is_url_blacklisted(self, url: str) -> bool:
        return any(
            re.match(pattern, url) for pattern in self.config.url_pattern_blacklist
        )

    def _content_type_not_allowed(self, content_type: str) -> bool:
        return content_type in self.config.unwanted_content_types

    def _build_request_target(
        self,
        url: str,
        headers: dict[str, str],
    ) -> tuple[str, dict[str, str], dict[str, str]]:
        resolved_target = resolve_crawl_target(url)

        request_headers = dict(headers)
        request_extensions: dict[str, str] = {}
        if resolved_target.host_header is not None:
            request_headers["Host"] = resolved_target.host_header
        if resolved_target.sni_hostname is not None:
            request_extensions["sni_hostname"] = resolved_target.sni_hostname

        return resolved_target.request_url, request_headers, request_extensions


def _markdownify_html_with_timeout(content: str, timeout: float) -> str:
    @timeout_decorator.timeout(timeout)
    def _markdownify_html(content: str) -> str:
        markdown = markdownify(
            content,
            heading_style="ATX",
        )

        return markdown

    try:
        return _markdownify_html(content)
    except Exception:
        _LOGGER.exception("Error markdownifying HTML")
        return "Unable to markdownify HTML"
