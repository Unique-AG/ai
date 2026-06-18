from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unique_search_proxy_sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy_sdk._generated.models.crawl_url_result import CrawlUrlResult
from unique_search_proxy_sdk._generated.models.per_url_error import PerUrlError

from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawler, BasicCrawlerConfig
from unique_web_search.services.crawlers.url_safety import ResolvedCrawlTarget
from unique_web_search.services.proxy.mappers import result_to_markdown


class TestBasicCrawlerFactory:
    def test_get_basic_crawler_service(self) -> None:
        config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)
        service = get_crawler_service(config)
        assert isinstance(service, BasicCrawler)
        assert service.config.crawler_type == CrawlerType.BASIC


class TestResultToMarkdown:
    def test_content_string(self) -> None:
        result = CrawlUrlResult(url="https://example.com", content="# Title")
        assert result_to_markdown(result) == "# Title"

    def test_per_url_error(self) -> None:
        result = CrawlUrlResult(
            url="https://example.com",
            error=PerUrlError(code="timeout", message="timed out"),
        )
        assert result_to_markdown(result) == "Error: timed out"

    def test_raw_string(self) -> None:
        result = CrawlUrlResult(
            url="https://example.com",
            raw="<html>body</html>",
        )
        assert result_to_markdown(result) == "<html>body</html>"

    def test_no_content_fallback(self) -> None:
        result = CrawlUrlResult(url="https://example.com")
        assert (
            result_to_markdown(result) == "Error: No content returned by search proxy"
        )


class TestBasicCrawlerProxyMode:
    @pytest.fixture
    def basic_config(self) -> BasicCrawlerConfig:
        return BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)

    @pytest.fixture
    def basic_crawler(self, basic_config: BasicCrawlerConfig) -> BasicCrawler:
        return BasicCrawler(basic_config)

    @pytest.fixture
    def resolved_targets(self) -> list[ResolvedCrawlTarget]:
        return [
            ResolvedCrawlTarget(
                normalized_url="https://example.com",
                hostname="example.com",
                resolved_ip="",
                used_dns_resolution=False,
            ),
            ResolvedCrawlTarget(
                normalized_url="https://missing.example",
                hostname="missing.example",
                resolved_ip="",
                used_dns_resolution=False,
            ),
        ]

    @pytest.mark.asyncio
    async def test_crawl_routes_to_proxy_when_enabled(
        self,
        basic_crawler: BasicCrawler,
        resolved_targets: list[ResolvedCrawlTarget],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_web_search.services.crawlers.basic.search_proxy_client_enabled",
            True,
        )
        monkeypatch.setattr(
            "unique_web_search.settings.env_settings.search_proxy_base_url",
            "http://search-proxy.local",
        )
        mock_client = AsyncMock()
        mock_client.crawl.basic = AsyncMock(
            return_value=CrawlResponse(
                results=[
                    CrawlUrlResult(
                        url="https://example.com",
                        content="markdown body",
                    ),
                    CrawlUrlResult(
                        url="https://missing.example",
                        content="missing",
                    ),
                ],
                crawler="Basic",
            )
        )
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "unique_web_search.services.proxy.bridge.UniqueSearchProxyClient",
            mock_client_cls,
        ):
            result = await basic_crawler._crawl(resolved_targets)

        mock_client.crawl.basic.assert_awaited_once()
        assert result == ["markdown body", "missing"]

    @pytest.mark.asyncio
    async def test_crawl_maps_successful_proxy_response(
        self,
        basic_crawler: BasicCrawler,
        resolved_targets: list[ResolvedCrawlTarget],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_web_search.services.crawlers.basic.search_proxy_client_enabled",
            True,
        )
        monkeypatch.setattr(
            "unique_web_search.settings.env_settings.search_proxy_base_url",
            "http://search-proxy.local",
        )
        mock_client = AsyncMock()
        mock_client.crawl.basic = AsyncMock(
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
            "unique_web_search.services.proxy.bridge.UniqueSearchProxyClient",
            mock_client_cls,
        ):
            result = await basic_crawler._crawl(resolved_targets)

        assert result == [
            "markdown body",
            "Error: URL not found in search proxy response",
        ]
        mock_client.crawl.basic.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_crawl_propagates_proxy_errors(
        self,
        basic_crawler: BasicCrawler,
        resolved_targets: list[ResolvedCrawlTarget],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_web_search.services.crawlers.basic.search_proxy_client_enabled",
            True,
        )
        monkeypatch.setattr(
            "unique_web_search.settings.env_settings.search_proxy_base_url",
            "http://search-proxy.local",
        )
        mock_client = AsyncMock()
        mock_client.crawl.basic = AsyncMock(
            side_effect=RuntimeError("connection refused")
        )
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "unique_web_search.services.proxy.bridge.UniqueSearchProxyClient",
                mock_client_cls,
            ),
            pytest.raises(RuntimeError, match="connection refused"),
        ):
            await basic_crawler._crawl(resolved_targets)
