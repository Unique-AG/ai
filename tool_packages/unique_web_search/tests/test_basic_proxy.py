from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unique_search_proxy_sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy_sdk._generated.models.crawl_url_result import CrawlUrlResult
from unique_search_proxy_sdk._generated.models.per_url_error import PerUrlError

import unique_web_search.client_settings as client_settings_module
from unique_web_search.client_settings import (
    SearchProxySettings,
    get_search_proxy_settings,
)
from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic_proxy import (
    BasicCrawlerProxyConfig,
    BasicProxyCrawler,
    _result_to_markdown,
)


class TestSearchProxySettings:
    def test_is_configured_when_base_url_set(self) -> None:
        settings = SearchProxySettings(base_url="http://search-proxy.local")
        assert settings.is_configured is True

    def test_is_configured_when_base_url_missing(self) -> None:
        settings = SearchProxySettings()
        assert settings.is_configured is False

    def test_from_env_settings_logs_warning_when_unconfigured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            client_settings_module.env_settings,
            "search_proxy_base_url",
            None,
        )
        settings = SearchProxySettings.from_env_settings()
        assert settings.base_url is None

    def test_from_env_settings_when_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            client_settings_module.env_settings,
            "search_proxy_base_url",
            "http://search-proxy.local",
        )
        settings = SearchProxySettings.from_env_settings()
        assert settings.base_url == "http://search-proxy.local"

    def test_get_search_proxy_settings_caches_singleton(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            client_settings_module,
            "_search_proxy_settings",
            None,
        )
        monkeypatch.setattr(
            client_settings_module.env_settings,
            "search_proxy_base_url",
            "http://search-proxy.local",
        )
        first = get_search_proxy_settings()
        second = get_search_proxy_settings()
        assert first is second


class TestBasicProxyCrawlerFactory:
    def test_get_basic_proxy_crawler_service(self) -> None:
        config = BasicCrawlerProxyConfig(crawler_type=CrawlerType.BASIC_PROXY)
        service = get_crawler_service(config)
        assert isinstance(service, BasicProxyCrawler)
        assert service.config.crawler_type == CrawlerType.BASIC_PROXY


class TestResultToMarkdown:
    def test_content_string(self) -> None:
        result = CrawlUrlResult(url="https://example.com", content="# Title")
        assert _result_to_markdown(result) == "# Title"

    def test_per_url_error(self) -> None:
        result = CrawlUrlResult(
            url="https://example.com",
            error=PerUrlError(code="timeout", message="timed out"),
        )
        assert _result_to_markdown(result) == "Error: timed out"

    def test_raw_string(self) -> None:
        result = CrawlUrlResult(
            url="https://example.com",
            raw="<html>body</html>",
        )
        assert _result_to_markdown(result) == "<html>body</html>"

    def test_no_content_fallback(self) -> None:
        result = CrawlUrlResult(url="https://example.com")
        assert (
            _result_to_markdown(result) == "Error: No content returned by search proxy"
        )


class TestBasicProxyCrawler:
    @pytest.fixture
    def proxy_config(self) -> BasicCrawlerProxyConfig:
        return BasicCrawlerProxyConfig(crawler_type=CrawlerType.BASIC_PROXY)

    @pytest.fixture
    def proxy_crawler(self, proxy_config: BasicCrawlerProxyConfig) -> BasicProxyCrawler:
        return BasicProxyCrawler(proxy_config)

    @pytest.mark.asyncio
    async def test_crawl_delegates_to_internal_crawl(
        self,
        proxy_crawler: BasicProxyCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_crawl = AsyncMock(return_value=["ok"])
        monkeypatch.setattr(proxy_crawler, "_crawl", mock_crawl)

        result = await proxy_crawler.crawl(["https://example.com"])

        mock_crawl.assert_awaited_once_with(["https://example.com"])
        assert result == ["ok"]

    @pytest.mark.asyncio
    async def test_crawl_maps_successful_proxy_response(
        self,
        proxy_crawler: BasicProxyCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_web_search.services.crawlers.basic_proxy.get_search_proxy_settings",
            lambda: SearchProxySettings(base_url="http://search-proxy.local"),
        )
        mock_client = AsyncMock()
        mock_client.crawl.crawl = AsyncMock(
            return_value=CrawlResponse(
                results=[
                    CrawlUrlResult(
                        url="https://example.com",
                        content="markdown body",
                    ),
                    CrawlUrlResult(
                        url="https://other.example",
                        content="other body",
                    ),
                ],
                crawler="Basic",
            )
        )
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "unique_web_search.services.crawlers.basic_proxy.UniqueSearchProxyClient",
            mock_client_cls,
        ):
            result = await proxy_crawler.crawl(
                ["https://example.com", "https://missing.example"]
            )

        assert result == [
            "markdown body",
            "Error: URL not found in search proxy response",
        ]
        mock_client.crawl.crawl.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_crawl_returns_errors_when_proxy_request_fails(
        self,
        proxy_crawler: BasicProxyCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_web_search.services.crawlers.basic_proxy.get_search_proxy_settings",
            lambda: SearchProxySettings(base_url="http://search-proxy.local"),
        )
        mock_client = AsyncMock()
        mock_client.crawl.crawl = AsyncMock(
            side_effect=RuntimeError("connection refused")
        )
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "unique_web_search.services.crawlers.basic_proxy.UniqueSearchProxyClient",
            mock_client_cls,
        ):
            result = await proxy_crawler.crawl(
                ["https://a.example", "https://b.example"]
            )

        assert result == [
            "Unable to crawl URL via search proxy: connection refused",
            "Unable to crawl URL via search proxy: connection refused",
        ]
