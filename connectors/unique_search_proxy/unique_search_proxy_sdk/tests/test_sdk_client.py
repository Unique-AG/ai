from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from unique_search_proxy_core.agent_engines.config_types import (
    ENGINE_NAME_TO_CONFIG as AGENT_ENGINE_NAME_TO_CONFIG,
)
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles
from unique_search_proxy_core.crawlers.config_types import CRAWLER_NAME_TO_CONFIG
from unique_search_proxy_core.search_engines.config_types import (
    ENGINE_NAME_TO_CONFIG as SEARCH_ENGINE_NAME_TO_CONFIG,
)

from unique_search_proxy_sdk import (
    AgentSearchClient,
    CrawlClient,
    SearchClient,
    UniqueSearchProxyClient,
)


@pytest_asyncio.fixture
async def sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[UniqueSearchProxyClient]:
    from unique_search_proxy_client.web.app import create_app
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


@pytest.mark.integration
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
        from unique_search_proxy_core.search_engines.google.schema import (
            GoogleSearchRequest,
        )

        async def fake_search(
            self: object,
            request: GoogleSearchRequest,
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

        response = await sdk_client.search.google(
            query="unique ag",
            fetch_size=3,
            gl="ch",
        )
        assert response.engine == "google"
        assert response.query == "unique ag"
        assert len(response.curated) == 1

    @pytest.mark.ai
    async def test_search_dispatcher_compat(
        self,
        sdk_client: UniqueSearchProxyClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy_core.schema import (
            SearchEngineRaw,
            WebSearchResult,
            WebSearchResults,
        )
        from unique_search_proxy_core.search_engines.google.schema import (
            GoogleSearchRequest,
        )

        async def fake_search(
            self: object,
            request: GoogleSearchRequest,
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

    @pytest.mark.ai
    async def test_search_validation_error(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        with pytest.raises(ValidationError):
            await sdk_client.search.search("")

    @pytest.mark.ai
    async def test_brave_provider_kwargs(
        self,
        sdk_client: UniqueSearchProxyClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy_core.schema import (
            SearchEngineRaw,
            WebSearchResult,
            WebSearchResults,
        )
        from unique_search_proxy_core.search_engines.brave.schema import (
            BraveSearchRequest,
        )

        async def fake_search(
            self: object,
            request: BraveSearchRequest,
        ) -> tuple[SearchEngineRaw, WebSearchResults]:
            assert request.country == "US"
            return SearchEngineRaw(pages=[]), WebSearchResults(
                results=[
                    WebSearchResult(url="https://example.com", title="t", snippet="s"),
                ],
            )

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.brave.service.BraveSearchService.search",
            fake_search,
        )
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")

        response = await sdk_client.search.brave(
            query="news",
            country="US",
            safesearch="strict",
        )
        assert response.engine == "brave"

    @pytest.mark.ai
    async def test_search_unknown_engine_raises(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        with pytest.raises(ValueError, match="Unknown search engine"):
            await sdk_client.search.search("q", engine="unknown")


@pytest.mark.integration
class TestCrawlClient:
    @pytest.mark.ai
    async def test_crawl_with_kwargs(
        self,
        sdk_client: UniqueSearchProxyClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlRequest
        from unique_search_proxy_core.schema import CrawlUrlResult

        async def fake_crawl(
            self: object,
            request: BasicCrawlRequest,
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

        response = await sdk_client.crawl.basic(
            urls=["https://example.com"],
            content_types=ContentTypeToggles(html=True),
        )
        assert response.crawler == CrawlerType.BASIC.value
        assert len(response.results) == 1
        assert response.results[0].url == "https://example.com"

    @pytest.mark.ai
    async def test_crawl_dispatcher_compat(
        self,
        sdk_client: UniqueSearchProxyClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlRequest
        from unique_search_proxy_core.schema import CrawlUrlResult

        async def fake_crawl(
            self: object,
            request: BasicCrawlRequest,
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
        assert response.crawler == CrawlerType.BASIC.value

    @pytest.mark.ai
    async def test_tavily_provider_kwargs(
        self,
        sdk_client: UniqueSearchProxyClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest
        from unique_search_proxy_core.schema import CrawlUrlResult

        async def fake_crawl(
            self: object,
            request: TavilyCrawlRequest,
        ) -> list[CrawlUrlResult]:
            assert request.extract_depth == "advanced"
            assert request.query == "rerank"
            return [
                CrawlUrlResult(
                    url=request.urls[0],
                    raw="markdown",
                    content_type="text/markdown",
                    content=None,
                ),
            ]

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.crawlers.tavily.service.TavilyCrawlerService.crawl",
            fake_crawl,
        )
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")

        response = await sdk_client.crawl.tavily(
            urls=["https://example.com"],
            extract_depth="advanced",
            query="rerank",
        )
        assert response.crawler == CrawlerType.TAVILY.value


class TestProviderRegistry:
    @pytest.mark.ai
    def test_search_providers_match_core_registry(self) -> None:
        from unique_search_proxy_sdk._transport import OpenapiTransport

        client = SearchClient(OpenapiTransport("http://test"))
        assert set(SEARCH_ENGINE_NAME_TO_CONFIG) == {"google", "brave", "perplexity"}
        for engine in SEARCH_ENGINE_NAME_TO_CONFIG:
            assert hasattr(client, engine)

    @pytest.mark.ai
    def test_agent_providers_match_core_registry(self) -> None:
        from unique_search_proxy_sdk._transport import OpenapiTransport

        client = AgentSearchClient(OpenapiTransport("http://test"))
        assert set(AGENT_ENGINE_NAME_TO_CONFIG) == {"bing", "vertexai"}
        for engine in AGENT_ENGINE_NAME_TO_CONFIG:
            assert hasattr(client, engine)
            assert hasattr(client, f"{engine}_stream")

    @pytest.mark.ai
    def test_crawl_providers_match_core_registry(self) -> None:
        from unique_search_proxy_sdk._transport import OpenapiTransport

        client = CrawlClient(OpenapiTransport("http://test"))
        expected = {"basic", "tavily", "jina", "firecrawl"}
        assert len(CRAWLER_NAME_TO_CONFIG) == len(expected)
        for attr in expected:
            assert hasattr(client, attr)


@pytest.mark.integration
class TestSubclientTypes:
    @pytest.mark.ai
    async def test_subclients_are_typed(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        assert isinstance(sdk_client.search, SearchClient)
        assert isinstance(sdk_client.crawl, CrawlClient)
        assert isinstance(sdk_client.agent_search, AgentSearchClient)
        assert callable(sdk_client.search.google)
        assert callable(sdk_client.crawl.basic)
        assert callable(sdk_client.agent_search.bing_stream)


class TestRequestContextHeaders:
    @pytest.mark.ai
    def test_client_sends_context_headers(self) -> None:
        from unique_search_proxy_core.context import (
            CHAT_ID_HEADER,
            COMPANY_ID_HEADER,
            USER_ID_HEADER,
            RequestContext,
        )

        from unique_search_proxy_sdk._transport import OpenapiTransport

        context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
        )
        transport = OpenapiTransport("http://test", context=context)
        headers = transport.openapi.get_async_httpx_client().headers
        assert headers[COMPANY_ID_HEADER] == "company-1"
        assert headers[USER_ID_HEADER] == "user-1"
        assert headers[CHAT_ID_HEADER] == "chat-1"

    @pytest.mark.ai
    async def test_v1_post_forwards_non_local_context(self) -> None:
        """The generated helpers default context headers to ``"local"`` and attach
        them per request; in httpx request headers win over client defaults, so the
        facade must forward the transport's context on every ``/v1`` POST.
        """
        from unique_search_proxy_core.context import (
            CHAT_ID_HEADER,
            COMPANY_ID_HEADER,
            USER_ID_HEADER,
            RequestContext,
        )

        from unique_search_proxy_sdk._transport import OpenapiTransport
        from unique_search_proxy_sdk.search_client import SearchClient

        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return httpx.Response(
                200,
                json={"engine": "google", "query": "q", "raw": {}, "curated": []},
            )

        context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
        )
        http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://test",
        )
        try:
            transport = OpenapiTransport(
                "http://test",
                http_client=http,
                context=context,
            )
            client = SearchClient(transport)
            await client.google(query="unique ag")
        finally:
            await http.aclose()

        assert captured[COMPANY_ID_HEADER] == "company-1"
        assert captured[USER_ID_HEADER] == "user-1"
        assert captured[CHAT_ID_HEADER] == "chat-1"
