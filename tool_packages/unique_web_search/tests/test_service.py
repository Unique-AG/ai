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
    """Test service components that can be tested without complex dependencies."""

    def test_web_search_tool_can_be_imported(self):
        """Test that WebSearchTool can be imported without errors."""
        from unique_web_search.service import WebSearchTool

        assert WebSearchTool is not None
        assert hasattr(WebSearchTool, "name")
        assert WebSearchTool.name == "WebSearch"

    def test_service_schema_integration(self):
        """Test that service schemas work correctly."""
        # Test WebSearchToolParameters
        params = WebSearchToolParameters(
            query="Service integration test", date_restrict="d1"
        )
        assert params.query == "Service integration test"
        assert params.date_restrict == "d1"

        # Test WebSearchPlan
        plan = WebSearchPlan(
            objective="Service test objective",
            query_analysis="Test analysis for service",
            steps=[],
            expected_outcome="Service integration outcome",
        )
        assert plan.objective == "Service test objective"
        assert len(plan.steps) == 0

    def test_service_dependencies_importable(self):
        """Test that service dependencies can be imported."""
        # Test executor imports

        assert WebSearchV1Executor is not None
        assert WebSearchV2Executor is not None

        # Test factory function imports

        assert get_search_engine_service is not None
        assert get_crawler_service is not None

    def test_search_engine_service_creation(self):
        """Test search engine service creation for the service."""
        from unique_web_search.services.search_engine import get_search_engine_service
        from unique_web_search.services.search_engine.google import GoogleSearch

        config = GoogleConfig(search_engine_name=SearchEngineType.GOOGLE)
        service = get_search_engine_service(config, Mock(), Mock())

        assert isinstance(service, GoogleSearch)
        assert hasattr(service, "search")
        assert hasattr(service, "requires_scraping")

    def test_crawler_service_creation(self):
        """Test crawler service creation for the service."""
        from unique_web_search.services.crawlers import get_crawler_service
        from unique_web_search.services.crawlers.basic import BasicCrawler

        config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)
        service = get_crawler_service(config)

        assert isinstance(service, BasicCrawler)
        assert hasattr(service, "crawl")

    def test_content_processing_for_service(self):
        """Test content processing components used by the service."""
        from unique_web_search.services.content_processing import WebPageChunk

        chunk = WebPageChunk(
            url="https://service-test.com",
            display_link="service-test.com",
            title="Service Test Page",
            snippet="Test snippet for service",
            content="Full content for service testing",
            order="1",
        )

        assert chunk.url == "https://service-test.com"
        assert chunk.title == "Service Test Page"

        # Test conversion to content chunk
        content_chunk = chunk.to_content_chunk()
        assert content_chunk.url == "https://service-test.com"
        assert content_chunk.text == "Full content for service testing"
        assert content_chunk.order == 1

    def test_utility_functions_for_service(self):
        """Test utility functions used by the service."""
        from unique_web_search.utils import query_params_to_human_string

        # Test the utility function the service uses
        result = query_params_to_human_string("service test query", "w2")
        assert result == "service test query (For the last 2 weeks)"

    def test_service_enums_and_types(self):
        """Test enums and types used by the service."""
        # Test CrawlerType
        assert CrawlerType.BASIC == "BasicCrawler"
        assert CrawlerType.CRAWL4AI == "Crawl4AiCrawler"
        assert CrawlerType.TAVILY == "TavilyCrawler"
        assert CrawlerType.FIRECRAWL == "FirecrawlCrawler"
        assert CrawlerType.JINA == "JinaCrawler"
        assert CrawlerType.NONE == "None"

        # Test SearchEngineType
        assert SearchEngineType.GOOGLE == "Google"
        assert SearchEngineType.JINA == "Jina"
        assert SearchEngineType.TAVILY == "Tavily"
        assert SearchEngineType.FIRECRAWL == "Firecrawl"
        assert SearchEngineType.BRAVE == "Brave"
        assert SearchEngineType.BING == "Bing"
        assert SearchEngineType.DUCKDUCKGO == "DuckDuckGo"

    def test_basic_configuration_components(self):
        """Test basic configuration components used by the service."""
        # Test BasicCrawlerConfig
        crawler_config = BasicCrawlerConfig(
            crawler_type=CrawlerType.BASIC, max_concurrent_requests=5
        )
        assert crawler_config.crawler_type == CrawlerType.BASIC
        assert crawler_config.max_concurrent_requests == 5

        # Test GoogleConfig
        search_config = GoogleConfig(
            search_engine_name=SearchEngineType.GOOGLE, fetch_size=8
        )
        assert search_config.search_engine_name == SearchEngineType.GOOGLE
        assert search_config.fetch_size == 8

    def test_service_step_types(self):
        """Test step types used by the service."""

        # Test search step
        search_step = Step(
            step_type=StepType.SEARCH,
            objective="Service search test",
            query_or_url="service search query",
        )
        assert search_step.step_type == StepType.SEARCH

        # Test read URL step
        url_step = Step(
            step_type=StepType.READ_URL,
            objective="Service URL read test",
            query_or_url="https://service-test.com/page",
        )
        assert url_step.step_type == StepType.READ_URL

    def test_service_tool_parameters_creation(self):
        """Test tool parameters creation from service perspective."""
        # Test creating custom parameters
        CustomParams = WebSearchToolParameters.from_tool_parameter_query_description(
            query_description="Service custom query description",
            date_restrict_description="Service date restriction",
        )

        params = CustomParams(query="service custom query", date_restrict="m3")

        assert params.query == "service custom query"
        assert params.date_restrict == "m3"

    @pytest.mark.ai
    def test_define_reference_list_for_message_log__returns_list__with_web_search_chunks(
        self,
    ):
        """
        Purpose: Verify define_reference_list_for_message_log returns list of references for web search.
        Why this matters: References link log entries to web search result URLs.
        Setup summary: Create web content chunks, call define_reference_list_for_message_log, verify returns list.
        """
        from unique_toolkit.content.schemas import ContentChunk, ContentReference

        from unique_web_search.service import WebSearchTool

        # Arrange
        content_chunks = [
            ContentChunk(
                id="chunk_1",
                text="Content from web page 1",
                url="https://example.com/page1",
                title="Page 1 Title",
            )
        ]
        data: list[ContentReference] = []

        # Act - Create a minimal instance to test the private method
        tool = WebSearchTool.__new__(
            WebSearchTool
        )  # Create instance without calling __init__
        references = tool._define_reference_list_for_message_log(
            content_chunks=content_chunks, data=data
        )

        # Assert
        assert isinstance(references, list)
        assert len(references) == 1

    @pytest.mark.ai
    def test_define_reference_list_for_message_log__sets_sequence_number__for_first_chunk(
        self,
    ):
        """
        Purpose: Verify define_reference_list_for_message_log sets sequence_number to 0 for first chunk.
        Why this matters: Sequence numbers order references in display.
        Setup summary: Create web content chunk, call define_reference_list_for_message_log, verify first reference sequence_number is 0.
        """
        from unique_toolkit.content.schemas import ContentChunk, ContentReference

        from unique_web_search.service import WebSearchTool

        # Arrange
        content_chunks = [
            ContentChunk(
                id="chunk_1",
                text="Content from web page 1",
                url="https://example.com/page1",
                title="Page 1 Title",
            )
        ]
        data: list[ContentReference] = []

        # Act - Create a minimal instance to test the private method
        tool = WebSearchTool.__new__(
            WebSearchTool
        )  # Create instance without calling __init__
        references = tool._define_reference_list_for_message_log(
            content_chunks=content_chunks, data=data
        )

        # Assert
        assert isinstance(references[0].sequence_number, int)
        assert references[0].sequence_number == 0

    @pytest.mark.ai
    def test_define_reference_list_for_message_log__sets_url__from_chunk_url(self):
        """
        Purpose: Verify define_reference_list_for_message_log sets URL from chunk URL.
        Why this matters: URL links reference to source web page.
        Setup summary: Create web content chunk with URL, call define_reference_list_for_message_log, verify reference URL matches.
        """
        from unique_toolkit.content.schemas import ContentChunk, ContentReference

        from unique_web_search.service import WebSearchTool

        # Arrange
        content_chunks = [
            ContentChunk(
                id="chunk_1",
                text="Content from web page 1",
                url="https://example.com/page1",
                title="Page 1 Title",
            )
        ]
        data: list[ContentReference] = []

        # Act - Create a minimal instance to test the private method
        tool = WebSearchTool.__new__(
            WebSearchTool
        )  # Create instance without calling __init__
        references = tool._define_reference_list_for_message_log(
            content_chunks=content_chunks, data=data
        )

        # Assert
        assert isinstance(references[0].url, str)
        assert references[0].url == "https://example.com/page1"

    @pytest.mark.ai
    def test_define_reference_list_for_message_log__sets_source__to_web(self):
        """
        Purpose: Verify define_reference_list_for_message_log sets source to "web" for web search.
        Why this matters: Source identifies where reference content originated.
        Setup summary: Create web content chunk, call define_reference_list_for_message_log, verify reference source is "web".
        """
        from unique_toolkit.content.schemas import ContentChunk, ContentReference

        from unique_web_search.service import WebSearchTool

        # Arrange
        content_chunks = [
            ContentChunk(
                id="chunk_1",
                text="Content from web page 1",
                url="https://example.com/page1",
                title="Page 1 Title",
            )
        ]
        data: list[ContentReference] = []

        # Act - Create a minimal instance to test the private method
        tool = WebSearchTool.__new__(
            WebSearchTool
        )  # Create instance without calling __init__
        references = tool._define_reference_list_for_message_log(
            content_chunks=content_chunks, data=data
        )

        # Assert
        assert isinstance(references[0].source, str)
        assert references[0].source == "web"

    @pytest.mark.ai
    def test_define_reference_list_for_message_log__sets_name__from_chunk_url(self):
        """
        Purpose: Verify define_reference_list_for_message_log sets name from chunk URL.
        Why this matters: Name is displayed to users as reference identifier.
        Setup summary: Create web content chunk with URL, call define_reference_list_for_message_log, verify reference name is URL.
        """
        from unique_toolkit.content.schemas import ContentChunk, ContentReference

        from unique_web_search.service import WebSearchTool

        # Arrange
        content_chunks = [
            ContentChunk(
                id="chunk_1",
                text="Content from web page 1",
                url="https://example.com/page1",
                title="Page 1 Title",
            )
        ]
        data: list[ContentReference] = []

        # Act - Create a minimal instance to test the private method
        tool = WebSearchTool.__new__(
            WebSearchTool
        )  # Create instance without calling __init__
        references = tool._define_reference_list_for_message_log(
            content_chunks=content_chunks, data=data
        )

        # Assert
        assert isinstance(references[0].name, str)
        assert references[0].name == "https://example.com/page1"

    @pytest.mark.ai
    def test_define_reference_list_for_message_log__increments_sequence_number__for_multiple_chunks(
        self,
    ):
        """
        Purpose: Verify define_reference_list_for_message_log increments sequence_number for multiple chunks.
        Why this matters: Multiple references must be ordered correctly.
        Setup summary: Create two web content chunks, call define_reference_list_for_message_log, verify sequence numbers increment.
        """
        from unique_toolkit.content.schemas import ContentChunk, ContentReference

        from unique_web_search.service import WebSearchTool

        # Arrange
        content_chunks = [
            ContentChunk(
                id="chunk_1",
                text="Content from web page 1",
                url="https://example.com/page1",
                title="Page 1 Title",
            ),
            ContentChunk(
                id="chunk_2",
                text="Content from web page 2",
                url="https://example.com/page2",
                title="Page 2 Title",
            ),
        ]
        data: list[ContentReference] = []

        # Act - Create a minimal instance to test the private method
        tool = WebSearchTool.__new__(
            WebSearchTool
        )  # Create instance without calling __init__
        references = tool._define_reference_list_for_message_log(
            content_chunks=content_chunks, data=data
        )

        # Assert
        assert isinstance(references[0].sequence_number, int)
        assert references[0].sequence_number == 0
        assert isinstance(references[1].sequence_number, int)
        assert references[1].sequence_number == 1

    @pytest.mark.ai
    def test_define_reference_list_for_message_log__skips_chunks__with_empty_url(self):
        """
        Purpose: Verify define_reference_list skips chunks with empty or None URL.
        Why this matters: Only chunks with valid URLs should be included in references.
        Setup summary: Create chunks with empty and None URLs, call define_reference_list_for_message_log, verify they are skipped.
        """
        from unique_toolkit.content.schemas import ContentChunk, ContentReference

        from unique_web_search.service import WebSearchTool

        # Arrange
        content_chunks = [
            ContentChunk(
                id="chunk_1",
                text="Content with URL",
                url="https://example.com/page1",
                title="Page 1 Title",
            ),
            ContentChunk(
                id="chunk_2",
                text="Content without URL",
                url="",
                title="Page 2 Title",
            ),
            ContentChunk(
                id="chunk_3",
                text="Content with None URL",
                url=None,
                title="Page 3 Title",
            ),
        ]
        data: list[ContentReference] = []

        # Act - Create a minimal instance to test the private method
        tool = WebSearchTool.__new__(
            WebSearchTool
        )  # Create instance without calling __init__
        references = tool._define_reference_list_for_message_log(
            content_chunks=content_chunks, data=data
        )

        # Assert
        assert len(references) == 1
        assert references[0].url == "https://example.com/page1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
