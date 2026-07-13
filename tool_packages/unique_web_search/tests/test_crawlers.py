from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicConfig

from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.basic import BasicCrawler
from unique_web_search.services.crawlers.registry import CRAWLER_REGISTRY
from unique_web_search.services.crawlers.url_safety import (
    BlockedCrawlTarget,
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
)
from unique_web_search.services.crawlers.utils import (
    EMAIL_DOMAINS,
    FIRST_NAMES,
    LAST_NAMES,
    SEPARATORS,
    generate_random_email,
    get_random_user_agent,
)

# ActivatedCrawler uses the registry's titled subclass; construct that in tests.
TitledBasicConfig = CRAWLER_REGISTRY[CrawlerType.BASIC].config_cls
assert issubclass(TitledBasicConfig, BasicConfig)


class TestCrawlerFactory:
    """Test the crawler factory function."""

    def test_get_basic_crawler_service(self):
        """Test getting basic crawler service."""
        config = TitledBasicConfig(crawler=CrawlerType.BASIC)
        service = get_crawler_service(config)
        assert isinstance(service, BasicCrawler)
        assert service.config.crawler == CrawlerType.BASIC


class TestBasicCrawlerConfig:
    """Test BasicConfig functionality."""

    def test_basic_crawler_config_creation(self):
        """Test creating BasicConfig."""
        config = TitledBasicConfig(crawler=CrawlerType.BASIC)

        assert config.crawler == CrawlerType.BASIC
        assert hasattr(config, "content_types")
        assert hasattr(config, "max_concurrent_requests")
        assert hasattr(config, "url_blocked_patterns")
        assert config.max_concurrent_requests == 10
        assert config.content_types.html is True
        assert config.content_types.pdf is False
        assert config.url_blocked_patterns == [r".*\.pdf$"]

    def test_basic_crawler_config_custom_values(self):
        """Test BasicConfig with custom values."""
        config = TitledBasicConfig(
            crawler=CrawlerType.BASIC,
            max_concurrent_requests=5,
            url_blocked_patterns=[r".*\.exe$", r".*\.zip$"],
        )

        assert config.max_concurrent_requests == 5
        assert r".*\.exe$" in config.url_blocked_patterns
        assert r".*\.zip$" in config.url_blocked_patterns


class TestBasicCrawler:
    """Test BasicCrawler functionality."""

    @pytest.fixture
    def basic_crawler(self):
        """Create a BasicCrawler instance."""
        config = TitledBasicConfig(crawler=CrawlerType.BASIC)
        return BasicCrawler(config)

    def test_basic_crawler_initialization(self, basic_crawler):
        """Test BasicCrawler initializes correctly."""
        assert isinstance(basic_crawler.config, BasicConfig)
        assert basic_crawler.config.crawler == CrawlerType.BASIC

    def test_basic_crawler_has_crawl_method(self, basic_crawler):
        """Test BasicCrawler has the expected crawl method."""
        assert hasattr(basic_crawler, "crawl")
        assert callable(getattr(basic_crawler, "crawl"))

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_basic_crawler_crawl__raises__when_url_policy_blocks_target(
        self,
        basic_crawler: BasicCrawler,
    ) -> None:
        """
        Purpose: Verify the crawler layer enforces the shared URL policy as a backstop.
        Why this matters: Future callers must not be able to bypass executor-level validation accidentally.
        Setup summary: Attempt to crawl a metadata URL directly through the crawler and assert the request is rejected before any fetch starts.
        """
        with pytest.raises(CrawlTargetValidationError):
            await basic_crawler.crawl(["http://169.254.169.254/latest/meta-data"])

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_basic_crawler_crawl__raises__when_request_time_resolution_blocks_target(
        self,
        basic_crawler: BasicCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify request-time safety failures are surfaced instead of being converted into generic crawl errors.
        Why this matters: DNS rebinding protection only works if the crawler propagates the security exception to the caller.
        Setup summary: Force the per-request crawl step to raise a validation error and assert the top-level crawl call preserves it.
        """

        monkeypatch.setattr(
            basic_crawler,
            "_crawl_url_with_client",
            AsyncMock(
                side_effect=CrawlTargetValidationError(
                    [
                        BlockedCrawlTarget(
                            hostname="localhost",
                            category="localhost",
                            reason="Target points to a localhost host",
                        )
                    ]
                )
            ),
        )
        monkeypatch.setattr(
            "unique_web_search.services.crawlers.base.UrlSafetyService.validate_batch_urls",
            AsyncMock(
                side_effect=lambda urls: [
                    ResolvedCrawlTarget(
                        normalized_url=url.strip(),
                        hostname="",
                        resolved_ip="",
                        used_dns_resolution=False,
                    )
                    for url in urls
                ]
            ),
        )

        with pytest.raises(CrawlTargetValidationError):
            await basic_crawler.crawl(["https://example.com"])


class TestCrawlerTypes:
    """Test crawler type definitions."""

    def test_crawler_type_values(self):
        """Test that CrawlerType enum has expected values."""
        assert CrawlerType.BASIC == "Basic"
        assert CrawlerType.FIRECRAWL == "Firecrawl"
        assert CrawlerType.JINA == "Jina"
        assert CrawlerType.TAVILY == "Tavily"

    def test_crawler_type_membership(self):
        """Test CrawlerType membership."""
        assert "Basic" in CrawlerType
        assert "Tavily" in CrawlerType
        assert "invalid_crawler" not in CrawlerType
        assert "Crawl4AiCrawler" not in CrawlerType
        assert "NoCrawler" not in CrawlerType


class TestGenerateRandomEmail:
    def test_returns_valid_email_format(self):
        email = generate_random_email()
        local, _, domain = email.rpartition("@")
        assert _ == "@"
        assert len(local) > 0
        assert domain in EMAIL_DOMAINS

    def test_local_part_uses_known_names(self):
        for _ in range(50):
            email = generate_random_email()
            local = email.split("@")[0]
            stripped = local.rstrip("0123456789")
            has_first = any(stripped.startswith(name) for name in FIRST_NAMES)
            has_last = any(stripped.endswith(name) for name in LAST_NAMES)
            assert has_first
            assert has_last

    def test_separator_is_from_allowed_set(self):
        for _ in range(50):
            email = generate_random_email()
            local = email.split("@")[0]
            stripped = local.rstrip("0123456789")
            for sep in SEPARATORS:
                if sep == "":
                    continue
                if sep in stripped:
                    parts = stripped.split(sep)
                    assert parts[0] in FIRST_NAMES
                    assert parts[1] in LAST_NAMES
                    break


class TestGetRandomUserAgent:
    def test_returns_string_with_email_suffix(self):
        ua = get_random_user_agent()
        assert isinstance(ua, str)
        assert ua.endswith(")")
        assert "(" in ua
        assert "@" in ua

    @patch("unique_web_search.services.crawlers.utils.UserAgent")
    def test_uses_chrome_user_agent(self, mock_ua_cls):
        mock_ua_cls.return_value.chrome = "Mozilla/5.0 FakeChrome/1.0"
        ua = get_random_user_agent()
        assert ua.startswith("Mozilla/5.0 FakeChrome/1.0 (")


class TestBasicCrawlerCrawlUrl:
    @pytest.fixture
    def basic_crawler(self):
        config = TitledBasicConfig(crawler=CrawlerType.BASIC)
        return BasicCrawler(config)

    @pytest.mark.asyncio
    async def test_crawl_url_returns_markdown(self, basic_crawler):
        html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
        response = httpx.Response(
            200,
            text=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=httpx.Request("GET", "https://example.com"),
        )
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response
        target = ResolvedCrawlTarget(
            normalized_url="https://example.com",
            hostname="example.com",
            resolved_ip="93.184.216.34",
            used_dns_resolution=True,
        )
        result = await basic_crawler._crawl_url_with_client(client, target)

        client.get.assert_called_once()
        call_headers = client.get.call_args[1].get(
            "headers",
            client.get.call_args[0][1] if len(client.get.call_args[0]) > 1 else None,
        )
        assert "User-Agent" in call_headers
        assert "@" in call_headers["User-Agent"]
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_crawl_url_pins_request_to_resolved_ip_for_https_targets(
        self,
        basic_crawler: BasicCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        html = "<html><body><p>Hello</p></body></html>"
        response = httpx.Response(
            200,
            text=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=httpx.Request("GET", "https://93.184.216.34/docs?q=1"),
        )
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response

        target = ResolvedCrawlTarget(
            normalized_url="https://example.com/docs?q=1",
            hostname="example.com",
            resolved_ip="93.184.216.34",
            used_dns_resolution=True,
        )

        await basic_crawler._crawl_url_with_client(client, target)

        client.get.assert_called_once()
        assert client.get.call_args.args[0] == "https://93.184.216.34/docs?q=1"
        call_headers = client.get.call_args.kwargs["headers"]
        assert call_headers["Host"] == "example.com"
        assert call_headers["User-Agent"]
        assert (
            client.get.call_args.kwargs["extensions"]["sni_hostname"] == "example.com"
        )

    @pytest.mark.asyncio
    async def test_crawl_url_rejects_disallowed_content_type(self, basic_crawler):
        response = httpx.Response(
            200,
            text="%PDF-1.4",
            headers={"content-type": "application/pdf"},
            request=httpx.Request("GET", "https://example.com/file.pdf"),
        )
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response
        target = ResolvedCrawlTarget(
            normalized_url="https://example.com/file.pdf",
            hostname="example.com",
            resolved_ip="",
            used_dns_resolution=False,
        )
        result = await basic_crawler._crawl_url_with_client(client, target)
        assert "not allowed" in result
        client.get.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_urls__returns_bypass_targets__when_safety_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify validate_urls returns pass-through targets without DNS-pinning when safety is disabled.
        Why this matters: BasicCrawler must use targets from validate_urls only; bypass must not require a second resolve.
        Setup summary: Disable url_safety_enabled on env_settings and assert request_url equals normalized_url.
        """
        import unique_search_proxy_core.url_safety.service as service_module
        from unique_search_proxy_core.url_safety import UrlSafetyService

        monkeypatch.setattr(
            service_module,
            "url_safety_settings",
            service_module.url_safety_settings.model_copy(update={"enabled": False}),
        )

        url = " https://example.com/page "
        targets = await UrlSafetyService.validate_batch_urls([url])

        assert len(targets) == 1
        assert targets[0].normalized_url == url.strip()
        assert targets[0].request_url == url.strip()
        assert targets[0].host_header is None
        assert targets[0].sni_hostname is None


class TestBaseCrawlerValidationFlow:
    """Test that BaseCrawler.crawl() delegates to validate_urls and uses the result."""

    @pytest.fixture
    def basic_crawler(self) -> BasicCrawler:
        return BasicCrawler(TitledBasicConfig(crawler=CrawlerType.BASIC))

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_crawl__passes_validated_urls_to__legacy_crawl(
        self,
        basic_crawler: BasicCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify BaseCrawler uses URLs returned by validate_urls.
        Why this matters: URL normalization and redirect resolution happen in validate_urls and must feed the crawl step.
        Setup summary: Mock validate_urls to return transformed URLs and assert _legacy_crawl receives exactly that list.
        """
        import unique_web_search.services.crawlers.base as base_module

        monkeypatch.setattr(base_module, "search_proxy_client_enabled", False)

        transformed_target = ResolvedCrawlTarget(
            normalized_url="https://example.com/final",
            hostname="example.com",
            resolved_ip="93.184.216.34",
            used_dns_resolution=True,
        )
        mock_validate_batch_urls = AsyncMock(return_value=[transformed_target])
        monkeypatch.setattr(
            base_module.UrlSafetyService,
            "validate_batch_urls",
            mock_validate_batch_urls,
        )
        mock_legacy_crawl = AsyncMock(return_value=["content"])
        monkeypatch.setattr(basic_crawler, "_legacy_crawl", mock_legacy_crawl)

        await basic_crawler.crawl([" https://example.com/start "])

        mock_validate_batch_urls.assert_called_once_with(
            [" https://example.com/start "]
        )
        mock_legacy_crawl.assert_called_once_with([transformed_target])

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_crawl__skips_url_validation__when_proxy_enabled(
        self,
        basic_crawler: BasicCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify proxy crawl bypasses client-side URL validation.
        Why this matters: URL safety is enforced on the proxy side; duplicate validation would be redundant.
        Setup summary: Enable proxy routing, mock _proxy_crawl, assert validate_batch_urls is not called.
        """
        import unique_web_search.services.crawlers.base as base_module

        monkeypatch.setattr(base_module, "search_proxy_client_enabled", True)
        mock_validate_batch_urls = AsyncMock()
        monkeypatch.setattr(
            base_module.UrlSafetyService,
            "validate_batch_urls",
            mock_validate_batch_urls,
        )
        mock_proxy_crawl = AsyncMock(return_value=["content"])
        monkeypatch.setattr(basic_crawler, "_proxy_crawl", mock_proxy_crawl)

        await basic_crawler.crawl(["https://example.com"])

        mock_validate_batch_urls.assert_not_called()
        mock_proxy_crawl.assert_called_once_with(["https://example.com"])

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_crawl__raises__when_validate_urls_rejects_target(
        self,
        basic_crawler: BasicCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify crawl aborts when shared URL validation fails.
        Why this matters: Crawler callers rely on URL policy failures being surfaced directly.
        Setup summary: Mock validate_urls to raise CrawlTargetValidationError and assert _legacy_crawl is never called.
        """
        import unique_web_search.services.crawlers.base as base_module

        monkeypatch.setattr(base_module, "search_proxy_client_enabled", False)

        mock_validate_batch_urls = AsyncMock(
            side_effect=CrawlTargetValidationError(
                [
                    BlockedCrawlTarget(
                        hostname="localhost",
                        category="localhost",
                        reason="Target points to a localhost host",
                    )
                ]
            )
        )
        monkeypatch.setattr(
            base_module.UrlSafetyService,
            "validate_batch_urls",
            mock_validate_batch_urls,
        )
        mock_legacy_crawl = AsyncMock(return_value=["content"])
        monkeypatch.setattr(
            basic_crawler,
            "_legacy_crawl",
            mock_legacy_crawl,
        )

        with pytest.raises(CrawlTargetValidationError):
            await basic_crawler.crawl(["https://example.com"])

        mock_legacy_crawl.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_proxy_crawl__dumps_config_into_generic_sdk_call(
        self,
        basic_crawler: BasicCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify centralized proxy dispatch dumps config fields into client.crawl.crawl.
        Why this matters: Crawlers must mirror the engine pattern (generic SDK call, no per-crawler proxy methods).
        Setup summary: Mock the proxy client and assert crawl is called with crawler + config fields.
        """
        # BasicCrawler overrides _proxy_crawl in the basic module (to drop the
        # tool-only url_blocked_patterns field), so patch the symbols the
        # override actually resolves — the basic module's, not the base module's.
        import unique_web_search.services.crawlers.basic as basic_module

        mock_response = MagicMock()
        mock_client = MagicMock()
        mock_client.crawl.crawl = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        monkeypatch.setattr(
            basic_module,
            "open_search_proxy_client",
            MagicMock(return_value=mock_client),
        )
        monkeypatch.setattr(
            basic_module,
            "map_crawl_response",
            MagicMock(return_value=["mapped"]),
        )

        result = await basic_crawler._proxy_crawl(["https://example.com"])

        assert result == ["mapped"]
        mock_client.crawl.crawl.assert_called_once()
        call_kwargs = mock_client.crawl.crawl.call_args.kwargs
        assert call_kwargs["urls"] == ["https://example.com"]
        assert call_kwargs["crawler"] == CrawlerType.BASIC
        assert "timeout" in call_kwargs
        assert "max_concurrent_requests" in call_kwargs
