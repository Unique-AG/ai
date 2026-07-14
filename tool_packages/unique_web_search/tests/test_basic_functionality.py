import pytest
from unique_search_proxy_core.agent_engines import AgentEngineType
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicConfig
from unique_search_proxy_core.search_engines import SearchEngineType
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
)

from unique_web_search.services.crawlers.registry import CRAWLER_REGISTRY
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.executors.v2.schema import Step, StepType, WebSearchPlan
from unique_web_search.services.search_engine.base import (
    LocalSearchEngineType,
)

TitledBasicConfig = CRAWLER_REGISTRY[CrawlerType.BASIC].config_cls
assert issubclass(TitledBasicConfig, BasicConfig)


class TestWebSearchSchema:
    """Test the schema models that we know work."""

    def test_web_search_tool_parameters_basic(self):
        """Test basic WebSearchToolParameters creation."""
        params = WebSearchToolParameters(query="Python programming")
        assert params.query == "Python programming"

    def test_web_search_tool_parameters_with_exposed_date(self):
        """Test WebSearchToolParameters with exposed date restriction."""
        config = GoogleConfig(date_restrict=ExposableStrOrNone(expose=True, value=None))
        Params = WebSearchToolParameters.with_exposed_params(
            config.exposed_params_model()
        )
        params = Params(query="Recent AI news", dateRestrict="w1")
        assert params.query == "Recent AI news"
        assert params.date_restrict == "w1"

    def test_step_creation(self):
        """Test Step model creation."""
        search_step = Step(
            step_type=StepType.SEARCH,
            objective="Find tutorials",
            query_or_url="Python tutorial",
        )
        assert search_step.step_type == StepType.SEARCH
        assert search_step.objective == "Find tutorials"
        assert search_step.query_or_url == "Python tutorial"

        url_step = Step(
            step_type=StepType.READ_URL,
            objective="Read article",
            query_or_url="https://example.com/article",
        )
        assert url_step.step_type == StepType.READ_URL
        assert url_step.objective == "Read article"
        assert url_step.query_or_url == "https://example.com/article"

    def test_web_search_plan_creation(self):
        """Test WebSearchPlan creation."""
        plan = WebSearchPlan(
            objective="Learn Python",
            query_analysis="User wants to learn Python programming",
            steps=[
                Step(
                    step_type=StepType.SEARCH,
                    objective="Find tutorials",
                    query_or_url="Python tutorial",
                )
            ],
            expected_outcome="Python learning resources",
        )
        assert plan.objective == "Learn Python"
        assert len(plan.steps) == 1
        assert plan.steps[0].step_type == StepType.SEARCH

    def test_step_type_enum(self):
        """Test StepType enum values."""
        assert StepType.SEARCH == "search"
        assert StepType.READ_URL == "read_url"


class TestConfigurationBasics:
    """Test basic configuration functionality."""

    def test_crawler_types_available(self):
        """Test that crawler types are properly defined."""

        assert CrawlerType.BASIC == "Basic"
        assert CrawlerType.FIRECRAWL == "Firecrawl"
        assert CrawlerType.JINA == "Jina"
        assert CrawlerType.TAVILY == "Tavily"

    def test_search_engine_types_available(self):
        """Test that search engine types are properly defined."""

        assert SearchEngineType.GOOGLE == "google"
        assert SearchEngineType.BRAVE == "brave"
        assert SearchEngineType.PERPLEXITY == "perplexity"
        assert AgentEngineType.BING == "bing"
        assert AgentEngineType.VERTEXAI == "vertexai"
        assert LocalSearchEngineType.CUSTOM_API == "custom_api"


class TestBasicConfiguration:
    """Test basic configuration models."""

    def test_basic_crawler_config(self):
        """Test BasicConfig creation."""

        config = TitledBasicConfig(crawler=CrawlerType.BASIC)
        assert config.crawler == CrawlerType.BASIC
        assert hasattr(config, "content_types")
        assert hasattr(config, "max_concurrent_requests")

    def test_google_search_config(self):
        """Test GoogleConfig creation."""

        config = GoogleConfig()
        assert config.engine == SearchEngineType.GOOGLE
        assert hasattr(config, "fetch_size")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
