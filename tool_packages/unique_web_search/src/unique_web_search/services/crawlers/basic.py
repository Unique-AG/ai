import asyncio
import logging
from typing import Annotated

import timeout_decorator
from httpx import AsyncClient, Timeout
from markdownify import markdownify
from pydantic import Field
from typing_extensions import override
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.content_types import (
    CONTENT_TYPE_TOGGLE_TO_MIME,
)
from unique_search_proxy_core.crawlers.basic.schema import (
    BasicConfig as CoreBasicConfig,
)
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_web_search.services.client.proxy_config import async_client
from unique_web_search.services.crawlers.base import BaseCrawler
from unique_web_search.services.crawlers.registry import register_crawler
from unique_web_search.services.crawlers.url_safety import (
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
)
from unique_web_search.services.crawlers.utils import get_random_user_agent
from unique_web_search.services.proxy.bridge import open_search_proxy_client
from unique_web_search.services.proxy.mappers import map_crawl_response

_LOGGER = logging.getLogger(__name__)


class BasicConfig(CoreBasicConfig):
    """Tool-local Basic crawler config; extends proxy-core with legacy URL filters."""

    url_blocked_patterns: Annotated[
        list[str],
        RJSFMetaTag({"ui:options": {"orderable": False}}),
    ] = Field(
        default_factory=lambda: [r".*\.pdf$"],
        title="URL blocked patterns",
        description=(
            "List of URL regex patterns to skip when crawling. "
            "**Note:** This field will be deprecated in the future."
        ),
    )


@register_crawler(
    name="basic",
    key=CrawlerType.BASIC,
    config_cls=BasicConfig,
    config_display_name="Basic",
)
class BasicCrawler(BaseCrawler[BasicConfig]):
    def __init__(self, config: BasicConfig):
        super().__init__(config)

        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(
            self.config.max_concurrent_requests
        )

    @override
    async def _proxy_crawl(self, urls: list[str]) -> list[str]:
        """Proxy crawl excludes tool-only fields the search-proxy schema forbids."""
        params = self.config.model_dump(
            exclude={"crawler", "url_blocked_patterns"},
            exclude_none=True,
        )
        async with open_search_proxy_client(
            timeout=float(self.config.timeout)
        ) as client:
            response = await client.crawl.crawl(
                urls=urls,
                crawler=self.config.crawler,
                **params,
            )
        return map_crawl_response(response, urls)

    @override
    async def _legacy_crawl(self, targets: list[ResolvedCrawlTarget]) -> list[str]:
        async with async_client(timeout=Timeout(self.config.timeout)) as client:
            tasks = [self._crawl_url_with_client(client, target) for target in targets]
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

    async def _crawl_url_with_client(
        self, client: AsyncClient, target: ResolvedCrawlTarget
    ) -> str:
        headers = {"User-Agent": get_random_user_agent()}

        request_headers = dict(headers)
        request_extensions: dict[str, str] = {}
        if target.host_header is not None:
            request_headers["Host"] = target.host_header
        if target.sni_hostname is not None:
            request_extensions["sni_hostname"] = target.sni_hostname

        response = await client.get(
            target.request_url,
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

    def _content_type_not_allowed(self, content_type: str) -> bool:
        allowed_mimes = {
            mime
            for field_name, mime in CONTENT_TYPE_TOGGLE_TO_MIME.items()
            if getattr(self.config.content_types, field_name)
        }
        return content_type not in allowed_mimes


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
