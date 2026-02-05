import asyncio
from unittest.mock import Mock

import pytest

from unique_web_search.schema import (
    Step,
    StepType,
    WebSearchPlan,
    WebSearchToolParameters,
)
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
    from unittest.mock import AsyncMock

    logger = Mock()
    logger.create_message_log_entry = Mock()
    logger.create_or_update_message_log_async = AsyncMock()
    return logger


@pytest.fixture
def mock_message_log():
    """Mock MessageLog for testing."""
    from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus

    return MessageLog(
        message_log_id="test-message-log-id",
        message_id="test-message-id",
        order=1,
        text="Test message log",
        status=MessageLogStatus.RUNNING,
    )


@pytest.fixture
def mock_tool_progress_reporter():
    """Mock tool progress reporter for WebSearchTool."""
    from unittest.mock import AsyncMock

    reporter = Mock(spec=["notify_from_tool_call"])
    reporter.notify_from_tool_call = AsyncMock()
    return reporter


@pytest.fixture
def sample_web_search_log_entries():
    """Sample WebSearchLogEntry list for testing.

    NOTE: WebSearchLogEntry was removed from the codebase.
    This fixture returns an empty list for backward compatibility.
    Tests should be refactored to use the message_log service instead.
    """
    return []


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


@pytest.fixture
def sample_web_search_results():
    """Sample WebSearchResult list for testing executors."""
    return [
        WebSearchResult(
            url="https://example.com/page1",
            title="Example Page 1",
            snippet="Snippet 1",
            content="Content 1",
        ),
        WebSearchResult(
            url="https://example.com/page2",
            title="Example Page 2",
            snippet="Snippet 2",
            content="Content 2",
        ),
    ]


@pytest.fixture
def mock_executor_dependencies():
    """Mock dependencies for executor initialization."""
    from unittest.mock import AsyncMock

    from unique_web_search.utils import WebSearchDebugInfo

    mock_lm_service = Mock()
    mock_lm_service.complete_async = AsyncMock()

    mock_lm = Mock()
    mock_lm.name = "test-model"

    mock_search_service = Mock()
    mock_search_service.search = AsyncMock(return_value=[])
    mock_search_service.requires_scraping = False
    mock_search_service.config = Mock()
    mock_search_service.config.search_engine_name = Mock()
    mock_search_service.config.search_engine_name.name = "TEST"

    mock_crawler_service = Mock()
    mock_crawler_service.crawl = AsyncMock(return_value=[])
    mock_crawler_service.config = Mock()
    mock_crawler_service.config.crawler_type = Mock()
    mock_crawler_service.config.crawler_type.name = "TEST"

    mock_content_processor = Mock()
    mock_content_processor.run = AsyncMock(return_value=[])
    mock_content_processor.config = Mock()
    mock_content_processor.config.strategy = Mock()
    mock_content_processor.config.strategy.name = "TEST"

    mock_message_log_callback = Mock()
    mock_message_log_callback.log_progress = AsyncMock()
    mock_message_log_callback.log_queries = AsyncMock()
    mock_message_log_callback.log_web_search_results = AsyncMock()

    mock_chunk_relevancy_sorter = Mock()
    mock_chunk_relevancy_sorter.run = AsyncMock(return_value=Mock(content_chunks=[]))

    mock_chunk_relevancy_sort_config = Mock()
    mock_chunk_relevancy_sort_config.enabled = False

    mock_content_reducer = Mock(return_value=[])

    mock_query_elicitation = AsyncMock(side_effect=lambda queries: queries)

    mock_tool_call = Mock()
    mock_tool_call.id = "test-tool-call-id"

    debug_info = WebSearchDebugInfo(parameters={})

    return {
        "language_model_service": mock_lm_service,
        "language_model": mock_lm,
        "search_service": mock_search_service,
        "crawler_service": mock_crawler_service,
        "content_processor": mock_content_processor,
        "message_log_callback": mock_message_log_callback,
        "chunk_relevancy_sorter": mock_chunk_relevancy_sorter,
        "chunk_relevancy_sort_config": mock_chunk_relevancy_sort_config,
        "content_reducer": mock_content_reducer,
        "query_elicitation": mock_query_elicitation,
        "tool_call": mock_tool_call,
        "debug_info": debug_info,
    }


@pytest.fixture
def executor_context_objects(mock_executor_dependencies: dict):
    """Create ExecutorServiceContext, ExecutorConfiguration, and ExecutorCallbacks from mock dependencies."""
    from unique_web_search.services.executors.context import (
        ExecutorCallbacks,
        ExecutorConfiguration,
        ExecutorServiceContext,
    )

    services = ExecutorServiceContext(
        search_engine_service=mock_executor_dependencies["search_service"],
        crawler_service=mock_executor_dependencies["crawler_service"],
        content_processor=mock_executor_dependencies["content_processor"],
        language_model_service=mock_executor_dependencies["language_model_service"],
        chunk_relevancy_sorter=mock_executor_dependencies["chunk_relevancy_sorter"],
    )

    config = ExecutorConfiguration(
        language_model=mock_executor_dependencies["language_model"],
        chunk_relevancy_sort_config=mock_executor_dependencies[
            "chunk_relevancy_sort_config"
        ],
        company_id="test-company",
        debug_info=mock_executor_dependencies["debug_info"],
    )

    callbacks = ExecutorCallbacks(
        message_log_callback=mock_executor_dependencies["message_log_callback"],
        content_reducer=mock_executor_dependencies["content_reducer"],
        query_elicitation=mock_executor_dependencies["query_elicitation"],
    )

    return {
        "services": services,
        "config": config,
        "callbacks": callbacks,
    }
