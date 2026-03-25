from unittest.mock import AsyncMock, patch

import httpx
import pytest

from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawler, BasicCrawlerConfig
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
        assert CrawlerType.NONE == "None"

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

        result = await basic_crawler._crawl_url_with_client(
            client, "https://example.com"
        )

        client.get.assert_called_once()
        call_headers = client.get.call_args[1].get(
            "headers",
            client.get.call_args[0][1] if len(client.get.call_args[0]) > 1 else None,
        )
        assert "User-Agent" in call_headers
        assert "@" in call_headers["User-Agent"]
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_crawl_url_blacklisted(self, basic_crawler):
        client = AsyncMock(spec=httpx.AsyncClient)
        result = await basic_crawler._crawl_url_with_client(
            client, "https://example.com/file.pdf"
        )
        assert "blacklisted" in result
        client.get.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
