from datetime import datetime
from logging import Logger
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.agentic.tools.agent_chunks_hanlder import AgentChunksHandler
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, Event
from unique_toolkit.content.schemas import Content, ContentChunk, ContentMetadata
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_internal_search.config import InternalSearchConfig


@pytest.fixture
def mock_logger() -> Logger:
    """Create a mock logger for testing."""
    logger: Logger = Mock(spec=Logger)
    return logger


@pytest.fixture
def mock_content_service() -> ContentService:
    """Create a mock ContentService for testing."""
    service: ContentService = Mock(spec=ContentService)
    service._metadata_filter = None
    return service


@pytest.fixture
def mock_chunk_relevancy_sorter() -> ChunkRelevancySorter:
    """Create a mock ChunkRelevancySorter for testing."""
    sorter: ChunkRelevancySorter = Mock(spec=ChunkRelevancySorter)
    return sorter


@pytest.fixture
def base_internal_search_config() -> InternalSearchConfig:
    """Create a base InternalSearchConfig for testing."""
    return InternalSearchConfig()


@pytest.fixture
def sample_content_chunk() -> ContentChunk:
    """Create a sample ContentChunk for testing."""
    return ContentChunk(
        id="chunk_123",
        text="Sample chunk text",
        order=1,
        start_page=1,
        end_page=2,
        metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
    )


@pytest.fixture
def sample_content_list() -> list[Any]:
    """Create a list of sample Content objects for testing."""
    # Using Mock to avoid Content schema validation issues
    content1 = Mock(spec=Content)
    content1.id = "content_1"
    content1.created_at = datetime(2024, 1, 2)
    content1.metadata = ContentMetadata(key="doc1.pdf", mime_type="application/pdf")

    content2 = Mock(spec=Content)
    content2.id = "content_2"
    content2.created_at = datetime(2024, 1, 1)
    content2.metadata = ContentMetadata(key="doc2.pdf", mime_type="application/pdf")

    return [content1, content2]


@pytest.fixture
def sample_content_chunks() -> list[ContentChunk]:
    """Create a list of sample ContentChunk objects for testing."""
    return [
        ContentChunk(
            id="chunk_1",
            text="First chunk",
            order=1,
            start_page=1,
            end_page=2,
            metadata=ContentMetadata(key="doc1.pdf", mime_type="application/pdf"),
        ),
        ContentChunk(
            id="chunk_2",
            text="Second chunk",
            order=2,
            start_page=3,
            end_page=4,
            metadata=ContentMetadata(key="doc2.pdf", mime_type="application/pdf"),
        ),
    ]


@pytest.fixture
def mock_base_event() -> BaseEvent:
    """Create a mock BaseEvent for testing."""
    event: BaseEvent = Mock(spec=BaseEvent)
    event.company_id = "company_123"
    event.user_id = "user_123"
    return event


@pytest.fixture
def mock_chat_event() -> ChatEvent:
    """Create a mock ChatEvent with chat_id for testing."""
    event: ChatEvent = Mock(spec=ChatEvent)
    event.company_id = "company_123"
    event.user_id = "user_123"
    payload = Mock()
    payload.chat_id = "chat_123"
    event.payload = payload
    return event


@pytest.fixture
def mock_event() -> Event:
    """Create a mock Event with chat_id for testing."""
    event: Event = Mock(spec=Event)
    event.company_id = "company_123"
    event.user_id = "user_123"
    payload = Mock()
    payload.chat_id = "chat_456"
    event.payload = payload
    return event


@pytest.fixture
def mock_language_model_function() -> LanguageModelFunction:
    """Create a mock LanguageModelFunction for testing."""
    tool_call: LanguageModelFunction = Mock(spec=LanguageModelFunction)
    tool_call.id = "tool_call_123"
    tool_call.arguments = {"search_string": "test query", "language": "english"}
    return tool_call


@pytest.fixture
def mock_tool_call_response() -> ToolCallResponse:
    """Create a mock ToolCallResponse for testing."""
    response: ToolCallResponse = Mock(spec=ToolCallResponse)
    response.id = "response_123"
    response.name = "InternalSearch"
    response.content_chunks = []
    response.debug_info = {}
    return response


@pytest.fixture
def mock_tool_progress_reporter() -> ToolProgressReporter:
    """Create a mock ToolProgressReporter for testing."""
    reporter: ToolProgressReporter = Mock(spec=ToolProgressReporter)
    reporter.notify_from_tool_call = AsyncMock()
    return reporter


@pytest.fixture
def mock_agent_chunks_handler() -> AgentChunksHandler:
    """Create a mock AgentChunksHandler for testing."""
    handler: AgentChunksHandler = Mock(spec=AgentChunksHandler)
    handler.chunks = []
    return handler
