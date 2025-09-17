import asyncio
from typing import Any, Literal

from httpx import AsyncClient
from pydantic import BaseModel, Field, HttpUrl

from unique_web_search.client_settings import get_jina_search_settings
from unique_web_search.services.crawlers.base import (
    BaseCrawler,
    BaseCrawlerConfig,
    CrawlerType,
)


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


class JinaCrawlerConfig(BaseCrawlerConfig[CrawlerType.JINA]):
    crawler_type: Literal[CrawlerType.JINA] = CrawlerType.JINA
    headers: dict[str, str] = Field(
        default={
            "X-Return-Format": "markdown",
            "X-Engine": "browser",
            "DNT": "1",
        },
        description="Headers to send with the request",
    )


class JinaCrawler(BaseCrawler[JinaCrawlerConfig]):
    def __init__(self, config: JinaCrawlerConfig):
        super().__init__(config)

    # TODO: Find a solution for tracking
    # @track(
    #     tags=["jina", "scrape"],
    # )
    async def crawl(self, urls: list[str]) -> list[str]:
        jina_settings = get_jina_search_settings()
        api_key = jina_settings.api_key
        assert api_key is not None
        reader_api_endpoint = jina_settings.reader_api_endpoint

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        } | self.config.headers

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
            "json": {"url": url},
        }
        response = await client.post(**params)
        return ReaderResponse.model_validate(response.json())
