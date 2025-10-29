from typing import Any
from unittest.mock import Mock

import pytest

from unique_web_search.schema import (
    Step,
    StepType,
    WebSearchPlan,
    WebSearchToolParameters,
)
from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawlerConfig
from unique_web_search.services.executors.web_search_v1_executor import (
    WebSearchV1Executor,
)
from unique_web_search.services.executors.web_search_v2_executor import (
    WebSearchV2Executor,
)
from unique_web_search.services.search_engine import get_search_engine_service
from unique_web_search.services.search_engine.base import SearchEngineType
from unique_web_search.services.search_engine.google import GoogleConfig


class TestWebSearchServiceComponents:
    """
    Test service components that can be tested without complex dependencies.

    These tests verify that service components can be imported, initialized,
    and integrated correctly without requiring full end-to-end service execution.
    """

    @pytest.mark.ai
    def test_web_search_tool__can_be_imported__without_errors(self) -> None:
        """
        Purpose: Verify WebSearchTool can be imported and has required attributes.
        Why this matters: Ensures service module is properly structured and accessible.
        Setup summary: Import WebSearchTool, assert class exists and has name attribute.
        """
        # Arrange & Act
        from unique_web_search.service import WebSearchTool

        # Assert
        assert WebSearchTool is not None
        assert hasattr(WebSearchTool, "name")
        assert WebSearchTool.name == "WebSearch"

    @pytest.mark.ai
    def test_service_schema_integration__works_correctly__for_parameters_and_plan(
        self,
    ) -> None:
        """
        Purpose: Verify service schemas integrate correctly with service components.
        Why this matters: Ensures schema models work properly in service context.
        Setup summary: Create WebSearchToolParameters and WebSearchPlan, assert values stored correctly.
        """
        # Arrange
        query: str = "Service integration test"
        date_restrict: str = "d1"

        # Act - Test WebSearchToolParameters
        params: WebSearchToolParameters = WebSearchToolParameters(
            query=query,
            date_restrict=date_restrict,
        )

        # Assert
        assert params.query == "Service integration test"
        assert params.date_restrict == "d1"

        # Arrange
        objective: str = "Service test objective"
        query_analysis: str = "Test analysis for service"
        steps: list[Step] = []
        expected_outcome: str = "Service integration outcome"

        # Act - Test WebSearchPlan
        plan: WebSearchPlan = WebSearchPlan(
            objective=objective,
            query_analysis=query_analysis,
            steps=steps,
            expected_outcome=expected_outcome,
        )

        # Assert
        assert plan.objective == "Service test objective"
        assert len(plan.steps) == 0

    @pytest.mark.ai
    def test_service_dependencies__can_be_imported__without_errors(self) -> None:
        """
        Purpose: Verify service dependencies can be imported successfully.
        Why this matters: Ensures all required service components are accessible.
        Setup summary: Import executor classes and factory functions, assert they exist.
        """
        # Arrange & Act & Assert
        assert WebSearchV1Executor is not None
        assert WebSearchV2Executor is not None
        assert get_search_engine_service is not None
        assert get_crawler_service is not None

    @pytest.mark.ai
    def test_search_engine_service__creates_correctly__with_google_config(self) -> None:
        """
        Purpose: Verify search engine service creation works for service integration.
        Why this matters: Ensures search engine factory works correctly in service context.
        Setup summary: Create GoogleConfig, call factory with mocked dependencies, assert GoogleSearch instance.
        """
        # Arrange
        from unique_web_search.services.search_engine.google import GoogleSearch

        config: GoogleConfig = GoogleConfig(search_engine_name=SearchEngineType.GOOGLE)

        # Act
        service: Any = get_search_engine_service(config, Mock(), Mock())

        # Assert
        assert isinstance(service, GoogleSearch)
        assert hasattr(service, "search")
        assert hasattr(service, "requires_scraping")

    @pytest.mark.ai
    def test_crawler_service__creates_correctly__with_basic_crawler_config(
        self,
    ) -> None:
        """
        Purpose: Verify crawler service creation works for service integration.
        Why this matters: Ensures crawler factory works correctly in service context.
        Setup summary: Create BasicCrawlerConfig, call factory, assert BasicCrawler instance.
        """
        # Arrange
        from unique_web_search.services.crawlers.basic import BasicCrawler

        config: BasicCrawlerConfig = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)

        # Act
        service: BasicCrawler = get_crawler_service(config)

        # Assert
        assert isinstance(service, BasicCrawler)
        assert hasattr(service, "crawl")

    @pytest.mark.ai
    def test_content_processing__works_correctly__for_service_components(self) -> None:
        """
        Purpose: Verify content processing components work correctly for service integration.
        Why this matters: Ensures content processing integrates properly with service workflow.
        Setup summary: Create WebPageChunk, convert to content chunk, assert conversion works correctly.
        """
        # Arrange
        from unique_web_search.services.content_processing import WebPageChunk

        chunk: WebPageChunk = WebPageChunk(
            url="https://service-test.com",
            display_link="service-test.com",
            title="Service Test Page",
            snippet="Test snippet for service",
            content="Full content for service testing",
            order="1",
        )

        # Assert
        assert chunk.url == "https://service-test.com"
        assert chunk.title == "Service Test Page"

        # Act - Test conversion to content chunk
        content_chunk = chunk.to_content_chunk()

        # Assert
        assert content_chunk.url == "https://service-test.com"
        assert content_chunk.text == "Full content for service testing"
        assert content_chunk.order == 1

    @pytest.mark.ai
    def test_utility_functions__work_correctly__for_service_integration(self) -> None:
        """
        Purpose: Verify utility functions work correctly for service integration.
        Why this matters: Ensures utility functions integrate properly with service workflow.
        Setup summary: Call query_params_to_human_string utility, assert formatted output correct.
        """
        # Arrange
        from unique_web_search.utils import query_params_to_human_string

        query: str = "service test query"
        date_restrict: str = "w2"

        # Act
        result: str = query_params_to_human_string(query, date_restrict)

        # Assert
        assert result == "service test query (For the last 2 weeks)"

    @pytest.mark.ai
    def test_service_enums_and_types__have_expected_values__for_all_types(self) -> None:
        """
        Purpose: Verify enums and types have expected values for service integration.
        Why this matters: Ensures type constants are correctly defined for service use.
        Setup summary: Assert CrawlerType and SearchEngineType constants equal expected values.
        """
        # Arrange & Act & Assert - CrawlerType
        assert CrawlerType.BASIC == "BasicCrawler"
        assert CrawlerType.CRAWL4AI == "Crawl4AiCrawler"
        assert CrawlerType.TAVILY == "TavilyCrawler"
        assert CrawlerType.FIRECRAWL == "FirecrawlCrawler"
        assert CrawlerType.JINA == "JinaCrawler"
        assert CrawlerType.NONE == "None"

        # Arrange & Act & Assert - SearchEngineType
        assert SearchEngineType.GOOGLE == "Google"
        assert SearchEngineType.JINA == "Jina"
        assert SearchEngineType.TAVILY == "Tavily"
        assert SearchEngineType.FIRECRAWL == "Firecrawl"
        assert SearchEngineType.BRAVE == "Brave"
        assert SearchEngineType.BING == "Bing"
        assert SearchEngineType.DUCKDUCKGO == "DuckDuckGo"

    @pytest.mark.ai
    def test_basic_configuration_components__work_correctly__for_service_integration(
        self,
    ) -> None:
        """
        Purpose: Verify basic configuration components work correctly for service integration.
        Why this matters: Ensures configuration models integrate properly with service.
        Setup summary: Create BasicCrawlerConfig and GoogleConfig, assert values stored correctly.
        """
        # Arrange & Act - Test BasicCrawlerConfig
        crawler_config: BasicCrawlerConfig = BasicCrawlerConfig(
            crawler_type=CrawlerType.BASIC,
            max_concurrent_requests=5,
        )

        # Assert
        assert crawler_config.crawler_type == CrawlerType.BASIC
        assert crawler_config.max_concurrent_requests == 5

        # Arrange & Act - Test GoogleConfig
        search_config: GoogleConfig = GoogleConfig(
            search_engine_name=SearchEngineType.GOOGLE,
            fetch_size=8,
        )

        # Assert
        assert search_config.search_engine_name == SearchEngineType.GOOGLE
        assert search_config.fetch_size == 8

    @pytest.mark.ai
    def test_service_step_types__work_correctly__for_search_and_read_url(self) -> None:
        """
        Purpose: Verify step types work correctly for service integration.
        Why this matters: Ensures step models integrate properly with service workflow.
        Setup summary: Create search and read URL steps, assert step types correct.
        """
        # Arrange & Act - Test search step
        search_step: Step = Step(
            step_type=StepType.SEARCH,
            objective="Service search test",
            query_or_url="service search query",
        )

        # Assert
        assert search_step.step_type == StepType.SEARCH

        # Arrange & Act - Test read URL step
        url_step: Step = Step(
            step_type=StepType.READ_URL,
            objective="Service URL read test",
            query_or_url="https://service-test.com/page",
        )

        # Assert
        assert url_step.step_type == StepType.READ_URL

    @pytest.mark.ai
    def test_service_tool_parameters__creates_custom_class__when_factory_called(
        self,
    ) -> None:
        """
        Purpose: Verify tool parameters factory works correctly for service integration.
        Why this matters: Ensures parameter customization works properly in service context.
        Setup summary: Call factory method with custom descriptions, create instance, assert values correct.
        """
        # Arrange
        query_description: str = "Service custom query description"
        date_restrict_description: str = "Service date restriction"

        # Act
        CustomParams = WebSearchToolParameters.from_tool_parameter_query_description(
            query_description=query_description,
            date_restrict_description=date_restrict_description,
        )
        params: WebSearchToolParameters = CustomParams(
            query="service custom query",
            date_restrict="m3",
        )

        # Assert
        assert params.query == "service custom query"
        assert params.date_restrict == "m3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
