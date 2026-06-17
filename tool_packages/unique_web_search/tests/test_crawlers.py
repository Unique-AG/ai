from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawler, BasicCrawlerConfig
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


class TestCrawlerFactory:
    """Test the crawler factory function."""

    def test_get_basic_crawler_service(self):
        """Test getting basic crawler service."""
        config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)
        service = get_crawler_service(config)
        assert isinstance(service, BasicCrawler)
        assert service.config.crawler_type == CrawlerType.BASIC


class TestBasicCrawlerConfig:
    """Test BasicCrawlerConfig functionality."""

    def test_basic_crawler_config_creation(self):
        """Test creating BasicCrawlerConfig."""
        config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)

        assert config.crawler_type == CrawlerType.BASIC
        assert hasattr(config, "url_pattern_blacklist")
        assert hasattr(config, "unwanted_content_types")
        assert hasattr(config, "max_concurrent_requests")

        # Test default values
        assert isinstance(config.url_pattern_blacklist, list)
        assert isinstance(config.unwanted_content_types, set)
        assert config.max_concurrent_requests == 10

    def test_basic_crawler_config_custom_values(self):
        """Test BasicCrawlerConfig with custom values."""
        config = BasicCrawlerConfig(
            crawler_type=CrawlerType.BASIC,
            max_concurrent_requests=5,
            url_pattern_blacklist=[r".*\.exe$", r".*\.zip$"],
        )

        assert config.max_concurrent_requests == 5
        assert r".*\.exe$" in config.url_pattern_blacklist
        assert r".*\.zip$" in config.url_pattern_blacklist


class TestBasicCrawler:
    """Test BasicCrawler functionality."""

    @pytest.fixture
    def basic_crawler(self):
        """Create a BasicCrawler instance."""
        config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)
        return BasicCrawler(config)

    def test_basic_crawler_initialization(self, basic_crawler):
        """Test BasicCrawler initializes correctly."""
        assert isinstance(basic_crawler.config, BasicCrawlerConfig)
        assert basic_crawler.config.crawler_type == CrawlerType.BASIC

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

    # Note: We're not testing the actual crawling functionality here
    # because it would require mocking HTTP requests and is complex.
    # The basic functionality tests verify the crawler can be created
    # and has the expected interface.


class TestCrawlerTypes:
    """Test crawler type definitions."""

    def test_crawler_type_values(self):
        """Test that CrawlerType enum has expected values."""
        assert CrawlerType.BASIC == "BasicCrawler"
        assert CrawlerType.CRAWL4AI == "Crawl4AiCrawler"
        assert CrawlerType.FIRECRAWL == "FirecrawlCrawler"
        assert CrawlerType.JINA == "JinaCrawler"
        assert CrawlerType.TAVILY == "TavilyCrawler"
        assert CrawlerType.NO_CRAWLER == "NoCrawler"

    def test_crawler_type_membership(self):
        """Test CrawlerType membership."""
        assert "BasicCrawler" in CrawlerType
        assert "Crawl4AiCrawler" in CrawlerType
        assert "invalid_crawler" not in CrawlerType


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
        config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)
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
    async def test_crawl_url_blacklisted(self, basic_crawler):
        client = AsyncMock(spec=httpx.AsyncClient)
        target = ResolvedCrawlTarget(
            normalized_url="https://example.com/file.pdf",
            hostname="example.com",
            resolved_ip="",
            used_dns_resolution=False,
        )
        result = await basic_crawler._crawl_url_with_client(client, target)
        assert "blacklisted" in result
        client.get.assert_not_called()

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
        return BasicCrawler(BasicCrawlerConfig(crawler_type=CrawlerType.BASIC))

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_crawl__passes_validated_urls_to__crawl(
        self,
        basic_crawler: BasicCrawler,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify BaseCrawler uses URLs returned by validate_urls.
        Why this matters: URL normalization and redirect resolution happen in validate_urls and must feed the crawl step.
        Setup summary: Mock validate_urls to return transformed URLs and assert _crawl receives exactly that list.
        """
        import unique_web_search.services.crawlers.base as base_module

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
        mock_crawl = AsyncMock(return_value=["content"])
        monkeypatch.setattr(basic_crawler, "_crawl", mock_crawl)

        await basic_crawler.crawl([" https://example.com/start "])

        mock_validate_batch_urls.assert_called_once_with(
            [" https://example.com/start "]
        )
        mock_crawl.assert_called_once_with([transformed_target])

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
        Setup summary: Mock validate_urls to raise CrawlTargetValidationError and assert _crawl is never called.
        """
        import unique_web_search.services.crawlers.base as base_module

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
        mock_crawl = AsyncMock(return_value=["content"])
        monkeypatch.setattr(
            basic_crawler,
            "_crawl",
            mock_crawl,
        )

        with pytest.raises(CrawlTargetValidationError):
            await basic_crawler.crawl(["https://example.com"])

        mock_crawl.assert_not_called()


class TestSsrfGuardHook:
    """Unit tests for the Playwright route interceptor installed by _ssrf_guard_hook.

    The hook is tested by:
    1. Calling _ssrf_guard_hook with a mock Page whose .route() captures the handler.
    2. Invoking the captured handler with mock Route / Request objects.
    3. Asserting route.abort() vs route.continue_() was called.

    This isolates the guard logic from the Chromium runtime without launching a
    real browser process.
    """

    async def _install_and_get_handler(self):
        """Install the hook on a mock page and return the captured route handler."""
        from unique_web_search.services.crawlers.crawl4ai import Crawl4AiCrawler

        captured: list = []

        async def fake_page_route(pattern: str, handler) -> None:
            captured.append((pattern, handler))

        mock_page = AsyncMock()
        mock_page.route = fake_page_route

        await Crawl4AiCrawler._get_ssrf_guard_hook()(
            mock_page,
            context=None,
            url="https://example.com",
            config=None,
        )

        assert len(captured) == 1, "hook must register exactly one route pattern"
        pattern, handler = captured[0]
        assert pattern == "**/*"
        return handler

    async def _invoke_handler(self, handler, url: str) -> tuple[AsyncMock, AsyncMock]:
        """Run the route handler for a given URL and return (route_mock, request_mock)."""
        mock_route = AsyncMock()
        mock_request = MagicMock()
        mock_request.url = url
        await handler(mock_route, mock_request)
        return mock_route, mock_request

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_ssrf_guard_hook__registers_wildcard_route_on_page(self) -> None:
        """
        Purpose: Verify the hook registers a '**/*' route handler on the page.
        Why this matters: Without a registered handler Chromium requests are never intercepted.
        Setup summary: Capture page.route calls; assert one handler is registered.
        """
        await self._install_and_get_handler()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_ssrf_guard_hook__aborts__for_metadata_ip(self) -> None:
        """
        Purpose: Verify requests to the AWS/GCP/Azure IMDS IP are aborted.
        Why this matters: IMDS access is the canonical SSRF target; guard must block it unconditionally.
        Setup summary: Route handler invoked with metadata URL; assert abort called.
        """
        handler = await self._install_and_get_handler()
        mock_route, _ = await self._invoke_handler(
            handler, "http://169.254.169.254/latest/meta-data"
        )

        mock_route.abort.assert_called_once_with("blockedbyclient")
        mock_route.continue_.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_ssrf_guard_hook__aborts__for_localhost_url(self) -> None:
        """
        Purpose: Verify requests to localhost are aborted (bypass A — redirect after HEAD 200).
        Why this matters: A server can return 200 on HEAD but 302→localhost on GET; the guard
        must catch the actual GET that Chromium issues after following the redirect.
        Setup summary: Route handler invoked with a localhost URL; assert abort called.
        """
        handler = await self._install_and_get_handler()
        mock_route, _ = await self._invoke_handler(handler, "http://localhost/internal")

        mock_route.abort.assert_called_once_with("blockedbyclient")
        mock_route.continue_.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_ssrf_guard_hook__aborts__for_private_ip(self) -> None:
        """
        Purpose: Verify requests to RFC-1918 addresses are aborted.
        Why this matters: Internal services often sit on 10.x / 192.168.x / 172.16.x; guard
        must block direct-IP accesses that bypass DNS.
        Setup summary: Route handler invoked with a private-IP URL; assert abort called.
        """
        handler = await self._install_and_get_handler()
        mock_route, _ = await self._invoke_handler(handler, "http://192.168.1.1/admin")

        mock_route.abort.assert_called_once_with("blockedbyclient")
        mock_route.continue_.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_ssrf_guard_hook__aborts__for_cluster_local_host(self) -> None:
        """
        Purpose: Verify requests to cluster-internal service names are aborted.
        Why this matters: Kubernetes service DNS names (*.svc.cluster.local) must not be
        reachable via a crafted redirect or JS fetch.
        Setup summary: Route handler invoked with a cluster-local URL; assert abort called.
        """
        handler = await self._install_and_get_handler()
        mock_route, _ = await self._invoke_handler(
            handler, "http://my-service.default.svc.cluster.local/secret"
        )

        mock_route.abort.assert_called_once_with("blockedbyclient")
        mock_route.continue_.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_ssrf_guard_hook__continues__for_public_url(self) -> None:
        """
        Purpose: Verify legitimate public requests are allowed through.
        Why this matters: The guard must not break normal crawl operations.
        Setup summary: Route handler invoked with a public URL; assert continue_ called.
        """
        handler = await self._install_and_get_handler()
        mock_route, _ = await self._invoke_handler(
            handler, "https://example.com/article"
        )

        mock_route.continue_.assert_called_once()
        mock_route.abort.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_ssrf_guard_hook__aborts__for_non_http_scheme(self) -> None:
        """
        Purpose: Verify non-http/https scheme URLs are aborted (e.g. file:// or ftp://).
        Why this matters: Chromium can sometimes be directed to fetch file:// URIs via
        crafted redirects; scheme allowlisting must be enforced at the route level.
        Setup summary: Route handler invoked with a file:// URL; assert abort called.
        """
        handler = await self._install_and_get_handler()
        mock_route, _ = await self._invoke_handler(handler, "file:///etc/passwd")

        mock_route.abort.assert_called_once_with("blockedbyclient")
        mock_route.continue_.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_crawl4ai_crawler_passes_ssrf_guard_hook_to_strategy_constructor(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify Crawl4AiCrawler._crawl passes _ssrf_guard_hook to AsyncPlaywrightCrawlerStrategy.
        Why this matters: Without hook registration the interceptor is never installed and all
        bypass vectors remain open.
        Setup summary: Mock AsyncPlaywrightCrawlerStrategy (top-level import) and AsyncWebCrawler
        (lazy import, patched at the crawl4ai source module); assert the strategy is constructed
        with hooks={'before_goto': _ssrf_guard_hook}.
        """
        from unique_web_search.services.crawlers.crawl4ai import (
            Crawl4AiCrawler,
            Crawl4AiCrawlerConfig,
        )

        mock_strategy_instance = MagicMock()
        mock_strategy_cls = MagicMock(return_value=mock_strategy_instance)

        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.crawler_strategy = mock_strategy_instance
        mock_crawler_instance.arun_many = AsyncMock(return_value=[])
        mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
        mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
        mock_async_web_crawler = MagicMock(return_value=mock_crawler_instance)

        # Both are lazy-imported inside _crawl, so patch them at their source modules.
        with (
            patch(
                "crawl4ai.async_webcrawler.AsyncPlaywrightCrawlerStrategy",
                mock_strategy_cls,
            ),
            patch("crawl4ai.AsyncWebCrawler", mock_async_web_crawler),
        ):
            crawler = Crawl4AiCrawler(
                Crawl4AiCrawlerConfig(crawler_type=CrawlerType.CRAWL4AI)
            )
            await crawler._crawl(
                [
                    ResolvedCrawlTarget(
                        normalized_url="https://example.com",
                        hostname="example.com",
                        resolved_ip="93.184.216.34",
                        used_dns_resolution=True,
                    )
                ]
            )

        mock_strategy_cls.assert_called_once()
        _, kwargs = mock_strategy_cls.call_args
        hooks = kwargs.get("hooks")
        assert hooks is not None
        assert "before_goto" in hooks
        # Each call to _get_ssrf_guard_hook() returns a new closure, so compare by name.
        assert callable(hooks["before_goto"])
        assert hooks["before_goto"].__name__ == "_ssrf_guard_hook"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_crawl4ai_crawler_omits_ssrf_guard_hook__when_safety_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify no before_goto hook is installed when url_safety_enabled=False.
        Why this matters: When safety is disabled the hook must be absent so Playwright is not restricted.
        Setup summary: Monkeypatch url_safety_enabled to False on BaseCrawler, run _crawl, and assert
        AsyncPlaywrightCrawlerStrategy receives an empty hooks dict.
        """
        import unique_web_search.services.crawlers.crawl4ai as crawl4ai_module
        from unique_web_search.services.crawlers.crawl4ai import (
            Crawl4AiCrawler,
            Crawl4AiCrawlerConfig,
        )

        monkeypatch.setattr(
            crawl4ai_module,
            "url_safety_settings",
            crawl4ai_module.url_safety_settings.model_copy(update={"enabled": False}),
        )

        mock_strategy_instance = MagicMock()
        mock_strategy_cls = MagicMock(return_value=mock_strategy_instance)

        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.crawler_strategy = mock_strategy_instance
        mock_crawler_instance.arun_many = AsyncMock(return_value=[])
        mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
        mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
        mock_async_web_crawler = MagicMock(return_value=mock_crawler_instance)

        with (
            patch(
                "crawl4ai.async_webcrawler.AsyncPlaywrightCrawlerStrategy",
                mock_strategy_cls,
            ),
            patch("crawl4ai.AsyncWebCrawler", mock_async_web_crawler),
        ):
            crawler = Crawl4AiCrawler(
                Crawl4AiCrawlerConfig(crawler_type=CrawlerType.CRAWL4AI)
            )
            await crawler._crawl(
                [
                    ResolvedCrawlTarget(
                        normalized_url="https://example.com",
                        hostname="example.com",
                        resolved_ip="",
                        used_dns_resolution=False,
                    )
                ]
            )

        _, kwargs = mock_strategy_cls.call_args
        hooks = kwargs.get("hooks")
        assert hooks == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
