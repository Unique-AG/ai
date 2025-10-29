import pytest

from unique_web_search.schema import (
    Step,
    StepType,
    WebSearchPlan,
    WebSearchToolParameters,
)
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawlerConfig
from unique_web_search.services.search_engine.base import SearchEngineType
from unique_web_search.services.search_engine.google import GoogleConfig
from unique_web_search.utils import query_params_to_human_string


class TestWebSearchSchema:
    """Test the schema models that we know work."""

    @pytest.mark.ai
    def test_web_search_tool_parameters__creates_with_query__when_no_date_restriction(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchToolParameters creates correctly with query and no date restriction.
        Why this matters: Ensures basic parameter creation works for search queries without time constraints.
        Setup summary: Create WebSearchToolParameters with query only, assert values stored correctly.
        """
        # Arrange
        query: str = "Python programming"

        # Act
        params: WebSearchToolParameters = WebSearchToolParameters(
            query=query,
            date_restrict=None,
        )

        # Assert
        assert params.query == "Python programming"
        assert params.date_restrict is None

    @pytest.mark.ai
    def test_web_search_tool_parameters__creates_with_date_restriction__when_provided(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchToolParameters accepts and stores date restriction value.
        Why this matters: Ensures time-bounded search queries are properly configured.
        Setup summary: Create WebSearchToolParameters with query and date_restrict, assert both values stored.
        """
        # Arrange
        query: str = "Recent AI news"
        date_restrict: str = "w1"

        # Act
        params: WebSearchToolParameters = WebSearchToolParameters(
            query=query,
            date_restrict=date_restrict,
        )

        # Assert
        assert params.query == "Recent AI news"
        assert params.date_restrict == "w1"

    @pytest.mark.ai
    def test_step__creates_search_step__with_search_type_and_query(self) -> None:
        """
        Purpose: Verify Step model creates correctly for search operations.
        Why this matters: Ensures search steps are properly structured in web search plans.
        Setup summary: Create Step with SEARCH type, objective, and query, assert all fields correct.
        """
        # Arrange
        step_type: StepType = StepType.SEARCH
        objective: str = "Find tutorials"
        query_or_url: str = "Python tutorial"

        # Act
        search_step: Step = Step(
            step_type=step_type,
            objective=objective,
            query_or_url=query_or_url,
        )

        # Assert
        assert search_step.step_type == StepType.SEARCH
        assert search_step.objective == "Find tutorials"
        assert search_step.query_or_url == "Python tutorial"

    @pytest.mark.ai
    def test_step__creates_read_url_step__with_read_url_type_and_url(self) -> None:
        """
        Purpose: Verify Step model creates correctly for URL reading operations.
        Why this matters: Ensures URL reading steps are properly structured in web search plans.
        Setup summary: Create Step with READ_URL type, objective, and URL, assert all fields correct.
        """
        # Arrange
        step_type: StepType = StepType.READ_URL
        objective: str = "Read article"
        query_or_url: str = "https://example.com/article"

        # Act
        url_step: Step = Step(
            step_type=step_type,
            objective=objective,
            query_or_url=query_or_url,
        )

        # Assert
        assert url_step.step_type == StepType.READ_URL
        assert url_step.objective == "Read article"
        assert url_step.query_or_url == "https://example.com/article"

    @pytest.mark.ai
    def test_web_search_plan__creates_with_steps__when_initialized(self) -> None:
        """
        Purpose: Verify WebSearchPlan creates correctly with objective, analysis, and steps.
        Why this matters: Ensures search plans are properly structured with all required components.
        Setup summary: Create WebSearchPlan with objective, query_analysis, steps, and expected_outcome, assert structure.
        """
        # Arrange
        objective: str = "Learn Python"
        query_analysis: str = "User wants to learn Python programming"
        steps: list[Step] = [
            Step(
                step_type=StepType.SEARCH,
                objective="Find tutorials",
                query_or_url="Python tutorial",
            ),
        ]
        expected_outcome: str = "Python learning resources"

        # Act
        plan: WebSearchPlan = WebSearchPlan(
            objective=objective,
            query_analysis=query_analysis,
            steps=steps,
            expected_outcome=expected_outcome,
        )

        # Assert
        assert plan.objective == "Learn Python"
        assert len(plan.steps) == 1
        assert plan.steps[0].step_type == StepType.SEARCH

    @pytest.mark.ai
    def test_step_type__has_expected_values__for_search_and_read_url(self) -> None:
        """
        Purpose: Verify StepType enum contains expected values for search and read operations.
        Why this matters: Ensures step type constants are correctly defined.
        Setup summary: Assert StepType constants equal expected string values.
        """
        # Arrange & Act & Assert
        assert StepType.SEARCH == "search"
        assert StepType.READ_URL == "read_url"


class TestUtilityFunctions:
    """Test utility functions."""

    @pytest.mark.ai
    def test_query_params_to_human_string__returns_query_only__when_no_date_restriction(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion returns query unchanged when no date restriction.
        Why this matters: Ensures proper formatting for queries without time constraints.
        Setup summary: Call function with query and None date_restrict, assert query returned unchanged.
        """
        # Arrange
        query: str = "Python tutorials"
        date_restrict: None = None

        # Act
        result: str = query_params_to_human_string(query, date_restrict)

        # Assert
        assert result == "Python tutorials"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_with_date__when_date_restriction_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats query with date restriction suffix.
        Why this matters: Ensures user-friendly date restriction display in search queries.
        Setup summary: Call function with query and date_restrict, assert formatted string with date suffix.
        """
        # Arrange
        query: str = "Recent news"
        date_restrict: str = "d7"

        # Act
        result: str = query_params_to_human_string(query, date_restrict)

        # Assert
        assert result == "Recent news (For the last 7 days)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_single_day__when_d1_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for single day restriction.
        Why this matters: Ensures proper grammar for singular day time periods.
        Setup summary: Call function with query and "d1", assert formatted string with singular day format.
        """
        # Arrange
        query: str = "Today's news"
        date_restrict: str = "d1"

        # Act
        result: str = query_params_to_human_string(query, date_restrict)

        # Assert
        assert result == "Today's news (For the last 1 day)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_weeks__when_w_prefix_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for week-based restrictions.
        Why this matters: Ensures proper formatting for weekly time periods.
        Setup summary: Call function with query and "w2", assert formatted string with weeks format.
        """
        # Arrange
        query: str = "Weekly report"
        date_restrict: str = "w2"

        # Act
        result: str = query_params_to_human_string(query, date_restrict)

        # Assert
        assert result == "Weekly report (For the last 2 weeks)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_months__when_m_prefix_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for month-based restrictions.
        Why this matters: Ensures proper formatting for monthly time periods.
        Setup summary: Call function with query and "m3", assert formatted string with months format.
        """
        # Arrange
        query: str = "Monthly data"
        date_restrict: str = "m3"

        # Act
        result: str = query_params_to_human_string(query, date_restrict)

        # Assert
        assert result == "Monthly data (For the last 3 months)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_years__when_y_prefix_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for year-based restrictions.
        Why this matters: Ensures proper formatting for yearly time periods.
        Setup summary: Call function with query and "y1", assert formatted string with years format.
        """
        # Arrange
        query: str = "Historical data"
        date_restrict: str = "y1"

        # Act
        result: str = query_params_to_human_string(query, date_restrict)

        # Assert
        assert result == "Historical data (For the last 1 year)"


class TestConfigurationBasics:
    """Test basic configuration functionality."""

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

    @pytest.mark.ai
    def test_search_engine_type__has_expected_values__for_common_engines(self) -> None:
        """
        Purpose: Verify SearchEngineType enum contains expected values for common engines.
        Why this matters: Ensures search engine type constants are correctly defined.
        Setup summary: Assert each SearchEngineType constant equals expected string value.
        """
        # Arrange & Act & Assert
        assert SearchEngineType.GOOGLE == "Google"
        assert SearchEngineType.JINA == "Jina"
        assert SearchEngineType.TAVILY == "Tavily"
        assert SearchEngineType.FIRECRAWL == "Firecrawl"


class TestBasicConfiguration:
    """Test basic configuration models."""

    @pytest.mark.ai
    def test_basic_crawler_config__creates_with_required_attributes__when_initialized(
        self,
    ) -> None:
        """
        Purpose: Verify BasicCrawlerConfig creates with required attributes present.
        Why this matters: Ensures proper configuration structure for basic crawler.
        Setup summary: Create BasicCrawlerConfig, assert crawler_type and required attributes exist.
        """
        # Arrange
        crawler_type: CrawlerType = CrawlerType.BASIC

        # Act
        config: BasicCrawlerConfig = BasicCrawlerConfig(crawler_type=crawler_type)

        # Assert
        assert config.crawler_type == CrawlerType.BASIC
        assert hasattr(config, "url_pattern_blacklist")
        assert hasattr(config, "unwanted_content_types")

    @pytest.mark.ai
    def test_google_search_config__creates_with_required_attributes__when_initialized(
        self,
    ) -> None:
        """
        Purpose: Verify GoogleConfig creates with required attributes present.
        Why this matters: Ensures proper configuration structure for Google search engine.
        Setup summary: Create GoogleConfig, assert search_engine_name and fetch_size attribute exist.
        """
        # Arrange
        engine_name: SearchEngineType = SearchEngineType.GOOGLE

        # Act
        config: GoogleConfig = GoogleConfig(search_engine_name=engine_name)

        # Assert
        assert config.search_engine_name == SearchEngineType.GOOGLE
        assert hasattr(config, "fetch_size")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
