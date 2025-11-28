import asyncio
from unittest.mock import Mock

import pytest

from unique_web_search.schema import (
    Step,
    StepType,
    WebSearchPlan,
    WebSearchToolParameters,
)
from unique_web_search.services.executors.base_executor import WebSearchLogEntry
from unique_web_search.services.executors.configs import WebSearchMode
from unique_web_search.services.search_engine.schema import WebSearchResult


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_web_search_tool_parameters():
    """Sample WebSearchToolParameters for testing."""
    return WebSearchToolParameters(
        query="Python web scraping best practices", date_restrict="m1"
    )


@pytest.fixture
def sample_web_search_plan():
    """Sample WebSearchPlan for testing."""
    return WebSearchPlan(
        objective="Find information about Python web scraping",
        query_analysis="User wants to learn about web scraping techniques in Python",
        steps=[
            Step(
                step_type=StepType.SEARCH,
                objective="Search for Python web scraping tutorials",
                query_or_url="Python web scraping tutorial BeautifulSoup requests",
            ),
            Step(
                step_type=StepType.READ_URL,
                objective="Read detailed guide",
                query_or_url="https://realpython.com/python-web-scraping-practical-introduction/",
            ),
        ],
        expected_outcome="Comprehensive guide on Python web scraping techniques",
    )


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("JINA_API_KEY", "test-jina-key")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-firecrawl-key")
    monkeypatch.setenv("BING_SUBSCRIPTION_KEY", "test-bing-key")
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave-key")


@pytest.fixture
def mock_web_search_config_v1():
    """Mock WebSearchConfig for V1 mode testing."""
    config = Mock()
    config.language_model = Mock()
    config.search_engine_config = Mock()
    config.crawler_config = Mock()
    config.content_processor_config = Mock()
    config.chunk_relevancy_sort_config = Mock()
    config.language_model_max_input_tokens = None
    config.percentage_of_input_tokens_for_sources = 0.4
    config.limit_token_sources = 60000
    config.debug = False
    config.tool_format_information_for_system_prompt = "Test format info"
    config.evaluation_check_list = []
    config.web_search_mode_config.mode = WebSearchMode.V1
    config.web_search_mode_config.tool_description = "V1 tool description"
    config.web_search_mode_config.tool_description_for_system_prompt = (
        "V1 system prompt"
    )
    config.web_search_mode_config.tool_parameters_description.query_description = (
        "Query description"
    )
    config.web_search_mode_config.tool_parameters_description.date_restrict_description = "Date restrict description"
    config.web_search_mode_config.refine_query_mode.mode = Mock()
    config.web_search_mode_config.max_queries = 5
    config.web_search_mode_config.refine_query_mode.system_prompt = (
        "Refine query prompt"
    )
    return config


@pytest.fixture
def mock_web_search_config_v2():
    """Mock WebSearchConfig for V2 mode testing."""
    config = Mock()
    config.language_model = Mock()
    config.search_engine_config = Mock()
    config.crawler_config = Mock()
    config.content_processor_config = Mock()
    config.chunk_relevancy_sort_config = Mock()
    config.language_model_max_input_tokens = None
    config.percentage_of_input_tokens_for_sources = 0.4
    config.limit_token_sources = 60000
    config.debug = False
    config.tool_format_information_for_system_prompt = "Test format info"
    config.evaluation_check_list = []
    config.web_search_mode_config.mode = WebSearchMode.V2
    config.web_search_mode_config.tool_description = "V2 tool description"
    config.web_search_mode_config.tool_description_for_system_prompt = (
        "V2 system prompt with $max_steps"
    )
    config.web_search_mode_config.max_steps = 5
    return config


@pytest.fixture
def mock_event():
    """Mock event object for WebSearchTool initialization."""
    event = Mock()
    event.company_id = "test-company-id"
    return event


@pytest.fixture
def mock_language_model_service():
    """Mock LanguageModelService for WebSearchTool initialization."""
    return Mock()


@pytest.fixture
def mock_chat_service():
    """Mock chat service for WebSearchTool initialization."""
    chat_service = Mock()
    chat_service.get_full_history.return_value = []
    return chat_service


@pytest.fixture
def mock_message_step_logger():
    """Mock message step logger for WebSearchTool."""
    logger = Mock()
    logger.create_message_log_entry = Mock()
    return logger


@pytest.fixture
def mock_tool_progress_reporter():
    """Mock tool progress reporter for WebSearchTool."""
    from unittest.mock import AsyncMock

    reporter = Mock(spec=["notify_from_tool_call"])
    reporter.notify_from_tool_call = AsyncMock()
    return reporter


@pytest.fixture
def sample_web_search_log_entries():
    """Sample WebSearchLogEntry list for testing."""
    result1 = WebSearchResult(
        url="https://example.com/page1",
        title="Example Page 1",
        snippet="Snippet 1",
        content="Content 1",
    )
    result2 = WebSearchResult(
        url="https://example.com/page2",
        title="Example Page 2",
        snippet="Snippet 2",
        content="Content 2",
    )
    return [
        WebSearchLogEntry(
            type=StepType.SEARCH,
            message="test query",
            web_search_results=[result1, result2],
        )
    ]


@pytest.fixture
def sample_content_chunks():
    """Sample ContentChunk list for testing."""
    from unique_toolkit.content import ContentChunk

    chunk1 = ContentChunk(
        id="example.com/page1",
        text="Test content 1",
        order=0,
        start_page=None,
        end_page=None,
        key="example.com/page1",
        chunk_id="0",
        url="https://example.com/page1",
        title="Test Page 1",
    )
    chunk2 = ContentChunk(
        id="example.com/page2",
        text="Test content 2",
        order=1,
        start_page=None,
        end_page=None,
        key="example.com/page2",
        chunk_id="1",
        url="https://example.com/page2",
        title="Test Page 2",
    )
    return [chunk1, chunk2]
