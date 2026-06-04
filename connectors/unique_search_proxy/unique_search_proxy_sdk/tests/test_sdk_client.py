from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles
from unique_search_proxy_core.search_engines.call_schema import (
    resolve_search_call_schema,
)

from unique_search_proxy_sdk import CrawlClient, SearchClient, UniqueSearchProxyClient


@pytest.fixture
async def sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[UniqueSearchProxyClient]:
    from unique_search_proxy_client.web.core.client.service import HttpClientPool

    async def mock_create_pool() -> HttpClientPool:
        http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(404)),
        )
        return HttpClientPool(client=http_client)

    monkeypatch.setattr(
        "unique_search_proxy_client.web.app.create_http_client_pool",
        mock_create_pool,
    )
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as http:
            client = UniqueSearchProxyClient("http://testserver", http_client=http)
            yield client


class TestSearchClient:
    @pytest.mark.ai
    async def test_search_with_kwargs(
        self,
        sdk_client: UniqueSearchProxyClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy_core.schema import (
            SearchEngineRaw,
            WebSearchResult,
            WebSearchResults,
        )
        from unique_search_proxy_core.search_engines.google.schema import GoogleRequest

        async def fake_search(
            self: object,
            request: GoogleRequest,
        ) -> tuple[SearchEngineRaw, WebSearchResults]:
            return SearchEngineRaw(pages=[]), WebSearchResults(
                results=[
                    WebSearchResult(url="https://example.com", title="t", snippet="s"),
                ],
            )

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.google.service.GoogleSearchService.search",
            fake_search,
        )
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-cx")

        response = await sdk_client.search.search(
            "unique ag",
            fetch_size=3,
            gl="ch",
        )
        assert response.engine == "google"
        assert response.query == "unique ag"
        assert len(response.curated) == 1

    @pytest.mark.ai
    async def test_search_validation_error(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        with pytest.raises(ValidationError):
            await sdk_client.search.search("")


class TestCrawlClient:
    @pytest.mark.ai
    async def test_crawl_with_kwargs(
        self,
        sdk_client: UniqueSearchProxyClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlerRequest
        from unique_search_proxy_core.schema import CrawlUrlResult

        async def fake_crawl(
            self: object,
            request: BasicCrawlerRequest,
        ) -> list[CrawlUrlResult]:
            return [
                CrawlUrlResult(
                    url=request.urls[0],
                    raw="<html>hi</html>",
                    content_type="text/html",
                    content=None,
                ),
            ]

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.crawlers.basic.service.BasicCrawlerService.crawl",
            fake_crawl,
        )

        response = await sdk_client.crawl.crawl(
            ["https://example.com"],
            content_types=ContentTypeToggles(html=True),
        )
        assert response.crawler_type == CrawlerType.BASIC.value
        assert len(response.results) == 1
        assert response.results[0].url == "https://example.com"


class TestCoreCallSchema:
    @pytest.mark.ai
    def test_resolve_search_call_schema_in_core(self) -> None:
        descriptor = resolve_search_call_schema("google")
        assert descriptor.engine == "google"
        assert descriptor.snippet_only is True
        assert "query" in descriptor.call_schema["properties"]
        assert "fetchSize" not in descriptor.call_schema["properties"]


class TestSubclientTypes:
    @pytest.mark.ai
    async def test_subclients_are_typed(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        assert isinstance(sdk_client.search, SearchClient)
        assert isinstance(sdk_client.crawl, CrawlClient)
