import pytest

from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawler, BasicCrawlerConfig


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
