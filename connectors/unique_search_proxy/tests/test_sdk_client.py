from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from unique_search_proxy.sdk import UniqueSearchProxyClient
from unique_search_proxy.sdk._generated.models.google_config_request import (
    GoogleConfigRequest as SdkGoogleConfigRequest,
)
from unique_search_proxy.web.app import create_app
from unique_search_proxy.web.core.crawlers.basic.schema import BasicCrawlerConfig
from unique_search_proxy.web.core.errors import (
    EngineNotConfiguredError,
    ValidationProxyError,
)


@pytest.fixture
async def sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[UniqueSearchProxyClient]:
    from unique_search_proxy.web.core.client.service import HttpClientPool

    async def mock_create_pool() -> HttpClientPool:
        http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(404)),
        )
        return HttpClientPool(client=http_client)

    monkeypatch.setattr(
        "unique_search_proxy.web.app.create_http_client_pool",
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


class TestUniqueSearchProxyClientConfiguration:
    @pytest.mark.ai
    async def test_list_providers(self, sdk_client: UniqueSearchProxyClient) -> None:
        providers = await sdk_client.list_providers()
        assert "google" in providers.search_engines
        assert "basic" in providers.crawlers

    @pytest.mark.ai
    async def test_search_engine_config_schema(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        schema = await sdk_client.search_engine_config_json_schema("google")
        assert schema.provider_id == "google"
        assert schema.json_schema["properties"]["engine"]["const"] == "google"

    @pytest.mark.ai
    async def test_search_engine_default_config(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        defaults = await sdk_client.search_engine_default_config("google")
        assert defaults.default_config["engine"] == "google"

    @pytest.mark.ai
    async def test_search_call_schema(
        self, sdk_client: UniqueSearchProxyClient
    ) -> None:
        result = await sdk_client.search_call_schema("google")
        assert result.engine == "google"
        assert result.snippet_only is True
        assert "query" in result.call_schema["properties"]
        assert "fetchSize" not in result.call_schema["properties"]

    @pytest.mark.ai
    async def test_unknown_engine_raises_engine_not_configured(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        with pytest.raises(EngineNotConfiguredError):
            await sdk_client.search_engine_config_json_schema("brave")


class TestUniqueSearchProxyClientValidation:
    @pytest.mark.ai
    async def test_search_validation_error(
        self,
        sdk_client: UniqueSearchProxyClient,
    ) -> None:
        with pytest.raises(ValidationProxyError):
            await sdk_client.search(
                SdkGoogleConfigRequest.from_dict(
                    {
                        "engine": "google",
                        "query": "",
                        "fetchSize": 10,
                        "timeout": 30,
                    },
                ),
            )


class TestUniqueSearchProxyClientCrawl:
    @pytest.mark.ai
    async def test_crawl_urls_mocked(
        self,
        sdk_client: UniqueSearchProxyClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy.web.core.schema import CrawlUrlResult

        async def fake_crawl(
            self: object,
            urls: list[str],
            *,
            timeout: int,
        ) -> list[CrawlUrlResult]:
            return [
                CrawlUrlResult(
                    url=urls[0],
                    raw="<html>hi</html>",
                    content_type="text/html",
                    content=None,
                ),
            ]

        monkeypatch.setattr(
            "unique_search_proxy.web.core.crawlers.basic.service.BasicCrawlerService.crawl",
            fake_crawl,
        )

        response = await sdk_client.crawl_urls(
            urls=["https://example.com"],
            config=BasicCrawlerConfig(),
        )
        assert response.crawler == "basic"
        assert len(response.results) == 1
        assert response.results[0].url == "https://example.com"
