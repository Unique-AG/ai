import asyncio
from typing import Any, override

from httpx import AsyncClient
from pydantic import BaseModel, Field, HttpUrl
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.jina.schema import JinaConfig

from unique_web_search.client_settings import get_jina_search_settings
from unique_web_search.services.crawlers.base import BaseCrawler
from unique_web_search.services.crawlers.registry import register_crawler
from unique_web_search.services.crawlers.url_safety import ResolvedCrawlTarget


class ReaderBody(BaseModel):
    url: HttpUrl = Field(..., description="The URL to fetch")


class ReaderData(BaseModel):
    title: str | None = None
    description: str | None = None
    url: str | None = None
    content: str | None = None
    images: dict[str, str] | None = None
    links: dict[str, str] | None = None
    usage: dict[str, Any] | None = None


class ReaderResponse(BaseModel):
    code: int
    status: int | None = None
    data: ReaderData | None = None


@register_crawler(
    name="jina",
    key=CrawlerType.JINA,
    config_cls=JinaConfig,
    config_display_name="Jina",
)
class JinaCrawler(BaseCrawler[JinaConfig]):
    def __init__(self, config: JinaConfig):
        super().__init__(config)

    @override
    async def _legacy_crawl(self, targets: list[ResolvedCrawlTarget]) -> list[str]:
        urls = [target.normalized_url for target in targets]

        jina_settings = get_jina_search_settings()
        api_key = jina_settings.api_key
        assert api_key is not None, "Jina API key is not configured"
        reader_api_endpoint = jina_settings.reader_api_endpoint

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with AsyncClient(timeout=self.config.timeout) as client:
            tasks = [
                self._crawl_url(url, headers, reader_api_endpoint, client)
                for url in urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        markdown_results = []

        for result in results:
            if isinstance(result, BaseException):
                markdown_results.append(f"Error: {result}")
                continue

            if result.code != 200:
                markdown_results.append(f"Error: {result.code}")
                continue

            if result.data and result.data.content:
                markdown_results.append(result.data.content)

        return markdown_results

    def _build_reader_body(self, url: str) -> dict[str, Any]:
        """Build the Jina Reader POST body applying all deployment config fields.

        Mirrors ``build_jina_reader_body`` on the search-proxy path so the direct
        (proxy-disabled) crawl honours the same ``JinaConfig`` fields.
        """
        config = self.config
        page_timeout = config.page_timeout
        if page_timeout is None:
            page_timeout = min(max(config.timeout, 1), 180)

        body: dict[str, Any] = {
            "url": url,
            "respondWith": config.return_format,
            "engine": config.engine,
            "timeout": page_timeout,
            "doNotTrack": config.do_not_track,
        }

        if config.no_cache:
            body["noCache"] = True
        if config.target_selector is not None:
            body["targetSelector"] = config.target_selector
        if config.wait_for_selector is not None:
            body["waitForSelector"] = config.wait_for_selector
        if config.remove_selector is not None:
            body["removeSelector"] = config.remove_selector
        if config.with_generated_alt:
            body["withGeneratedAlt"] = True
        if config.with_links_summary:
            body["withLinksSummary"] = True
        if config.with_images_summary:
            body["withImagesSummary"] = True
        if config.with_iframe:
            body["withIframe"] = True
        if config.retain_images is not None:
            body["retainImages"] = config.retain_images
        if config.locale is not None:
            body["locale"] = config.locale
        if config.referer is not None:
            body["referer"] = config.referer
        if config.proxy_url is not None:
            body["proxyUrl"] = config.proxy_url

        return body

    async def _crawl_url(
        self,
        url: str,
        headers: dict[str, str],
        reader_api_endpoint: str,
        client: AsyncClient,
    ) -> ReaderResponse:
        params = {
            "url": reader_api_endpoint,
            "headers": headers,
            "json": self._build_reader_body(url),
        }
        response = await client.post(**params)
        return ReaderResponse.model_validate(response.json())
