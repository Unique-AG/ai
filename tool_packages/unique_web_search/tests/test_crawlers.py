import pytest

from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawler, BasicCrawlerConfig


class TestCrawlerFactory:
    """Test the crawler factory function."""

    @pytest.mark.ai
    def test_get_crawler_service__returns_basic_crawler__with_basic_crawler_config(
        self,
    ) -> None:
        """
        Purpose: Verify factory returns BasicCrawler instance for BasicCrawlerConfig.
        Why this matters: Ensures correct crawler service instantiation for basic crawler.
        Setup summary: Create BasicCrawlerConfig, call factory, assert BasicCrawler instance returned.
        """
        # Arrange
        config: BasicCrawlerConfig = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)

        # Act
        service: BasicCrawler = get_crawler_service(config)

        # Assert
        assert isinstance(service, BasicCrawler)
        assert service.config.crawler_type == CrawlerType.BASIC


class TestBasicCrawlerConfig:
    """Test BasicCrawlerConfig functionality."""

    @pytest.mark.ai
    def test_basic_crawler_config__creates_with_defaults__when_only_crawler_type_provided(
        self,
    ) -> None:
        """
        Purpose: Verify BasicCrawlerConfig creates with default values and required attributes.
        Why this matters: Ensures proper default configuration for basic crawler.
        Setup summary: Create BasicCrawlerConfig with only crawler_type, assert defaults and attributes present.
        """
        # Arrange
        crawler_type: CrawlerType = CrawlerType.BASIC

        # Act
        config: BasicCrawlerConfig = BasicCrawlerConfig(crawler_type=crawler_type)

        # Assert
        assert config.crawler_type == CrawlerType.BASIC
        assert hasattr(config, "url_pattern_blacklist")
        assert hasattr(config, "unwanted_content_types")
        assert hasattr(config, "max_concurrent_requests")
        assert isinstance(config.url_pattern_blacklist, list)
        assert isinstance(config.unwanted_content_types, set)
        assert config.max_concurrent_requests == 10

    @pytest.mark.ai
    def test_basic_crawler_config__sets_custom_values__when_custom_parameters_provided(
        self,
    ) -> None:
        """
        Purpose: Verify BasicCrawlerConfig accepts and stores custom configuration values.
        Why this matters: Ensures flexibility in configuring crawler behavior.
        Setup summary: Create BasicCrawlerConfig with custom values, assert all values stored correctly.
        """
        # Arrange
        crawler_type: CrawlerType = CrawlerType.BASIC
        max_concurrent_requests: int = 5
        url_pattern_blacklist: list[str] = [r".*\.exe$", r".*\.zip$"]

        # Act
        config: BasicCrawlerConfig = BasicCrawlerConfig(
            crawler_type=crawler_type,
            max_concurrent_requests=max_concurrent_requests,
            url_pattern_blacklist=url_pattern_blacklist,
        )

        # Assert
        assert config.max_concurrent_requests == 5
        assert r".*\.exe$" in config.url_pattern_blacklist
        assert r".*\.zip$" in config.url_pattern_blacklist


class TestBasicCrawler:
    """Test BasicCrawler functionality."""

    @pytest.fixture
    def basic_crawler(self) -> BasicCrawler:
        """Create a BasicCrawler instance."""
        config: BasicCrawlerConfig = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)
        return BasicCrawler(config)

    @pytest.mark.ai
    def test_basic_crawler__initializes_correctly__with_basic_crawler_config(
        self, basic_crawler: BasicCrawler
    ) -> None:
        """
        Purpose: Verify BasicCrawler initializes with config correctly.
        Why this matters: Ensures crawler instance has correct structure and configuration.
        Setup summary: Use fixture BasicCrawler, assert config type and crawler_type correct.
        """
        # Arrange & Act (done by fixture)
        # Assert
        assert isinstance(basic_crawler.config, BasicCrawlerConfig)
        assert basic_crawler.config.crawler_type == CrawlerType.BASIC

    @pytest.mark.ai
    def test_basic_crawler__has_crawl_method__when_initialized(
        self, basic_crawler: BasicCrawler
    ) -> None:
        """
        Purpose: Verify BasicCrawler has the expected crawl method interface.
        Why this matters: Ensures crawler implements required interface for crawling operations.
        Setup summary: Use fixture BasicCrawler, assert crawl method exists and is callable.
        """
        # Arrange & Act (done by fixture)
        # Assert
        assert hasattr(basic_crawler, "crawl")
        assert callable(getattr(basic_crawler, "crawl"))


class TestCrawlerTypes:
    """Test crawler type definitions."""

    @pytest.mark.ai
    def test_crawler_type__has_expected_values__for_all_crawler_types(self) -> None:
        """
        Purpose: Verify CrawlerType enum contains all expected crawler type values.
        Why this matters: Ensures all supported crawlers are properly defined.
        Setup summary: Assert each CrawlerType constant equals expected string value.
        """
        # Arrange & Act & Assert
        assert CrawlerType.BASIC == "BasicCrawler"
        assert CrawlerType.CRAWL4AI == "Crawl4AiCrawler"
        assert CrawlerType.FIRECRAWL == "FirecrawlCrawler"
        assert CrawlerType.JINA == "JinaCrawler"
        assert CrawlerType.TAVILY == "TavilyCrawler"
        assert CrawlerType.NO_CRAWLER == "NoCrawler"
        assert CrawlerType.NONE == "None"

    @pytest.mark.ai
    def test_crawler_type__validates_membership__for_valid_and_invalid_names(
        self,
    ) -> None:
        """
        Purpose: Verify CrawlerType membership operator correctly identifies valid and invalid names.
        Why this matters: Ensures type safety when checking crawler type validity.
        Setup summary: Assert valid names are in CrawlerType, invalid name is not.
        """
        # Arrange & Act & Assert
        assert "BasicCrawler" in CrawlerType
        assert "Crawl4AiCrawler" in CrawlerType
        assert "invalid_crawler" not in CrawlerType


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
