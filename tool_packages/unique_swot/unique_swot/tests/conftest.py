"""Shared test fixtures and configurations for SWOT analysis tests."""

from unittest.mock import Mock

import pytest
from unique_toolkit.content.schemas import ContentChunk

from unique_swot.services.collection.schema import Source, SourceChunk, SourceType
from unique_swot.services.schemas import SWOTOperation, SWOTPlan, SWOTStepPlan


@pytest.fixture
def mock_knowledge_base_service():
    """Mock KnowledgeBaseService for testing."""
    service = Mock()
    service.search_content.return_value = []
    service.upload_content_from_bytes.return_value = Mock(id="test_content_id")
    service.download_content_to_bytes.return_value = b'{"test": "data"}'
    return service


@pytest.fixture
def mock_language_model_service():
    """Mock LanguageModelService for testing."""
    service = Mock()
    service.generate_text.return_value = "Generated text"
    service.generate_structured_output = Mock()
    return service


@pytest.fixture
def mock_short_term_memory_service():
    """Mock ShortTermMemoryService for testing."""
    service = Mock()
    service.create_memory.return_value = None
    service.find_latest_memory.return_value = None
    return service


@pytest.fixture
def mock_chat_service():
    """Mock ChatService for testing."""
    service = Mock()
    service._assistant_message_id = "test_message_id"
    service.create_message_log.return_value = Mock(message_log_id="test_log_id")
    service.create_message_execution.return_value = None
    service.update_message_execution.return_value = None
    service.modify_assistant_message.return_value = None
    return service


@pytest.fixture
def sample_content_chunk():
    """Create a sample ContentChunk for testing."""
    return ContentChunk(
        id="content_123",
        chunk_id="chunk_456",
        title="Test Document",
        key="test_doc.pdf",
        text="This is sample content for testing.",
        start_page=1,
        end_page=2,
    )


@pytest.fixture
def sample_source():
    """Create a sample Source for testing."""
    return Source(
        type=SourceType.KNOWLEDGE_BASE,
        url="https://example.com/doc",
        title="Test Source",
        chunks=[
            SourceChunk(id="chunk_1", text="This is chunk 1 content."),
            SourceChunk(id="chunk_2", text="This is chunk 2 content."),
        ],
    )


@pytest.fixture
def sample_sources(sample_source):
    """Create a list of sample sources for testing."""
    return [
        sample_source,
        Source(
            type=SourceType.WEB,
            url="https://example.com/web",
            title="Web Source",
            chunks=[
                SourceChunk(id="chunk_3", text="Web content chunk."),
            ],
        ),
    ]


@pytest.fixture
def sample_swot_step_plan():
    """Create a sample SWOTStepPlan for testing."""
    return SWOTStepPlan(
        operation=SWOTOperation.GENERATE,
        modify_instruction=None,
    )


@pytest.fixture
def sample_swot_plan(sample_swot_step_plan):
    """Create a sample SWOTPlan for testing."""
    return SWOTPlan(
        objective="Analyze company X's competitive position",
        strengths=sample_swot_step_plan,
        weaknesses=sample_swot_step_plan,
        opportunities=sample_swot_step_plan,
        threats=sample_swot_step_plan,
    )


@pytest.fixture
def sample_modify_swot_plan():
    """Create a sample SWOTPlan with modify operations."""
    return SWOTPlan(
        objective="Update existing SWOT analysis",
        strengths=SWOTStepPlan(
            operation=SWOTOperation.MODIFY,
            modify_instruction="Update with new data",
        ),
        weaknesses=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED,
            modify_instruction=None,
        ),
        opportunities=SWOTStepPlan(
            operation=SWOTOperation.GENERATE,
            modify_instruction=None,
        ),
        threats=SWOTStepPlan(
            operation=SWOTOperation.MODIFY,
            modify_instruction="Add recent threats",
        ),
    )


@pytest.fixture
def mock_notifier():
    """Mock Notifier for testing."""
    notifier = Mock()
    notifier.notify.return_value = None
    return notifier


@pytest.fixture
def mock_event():
    """Mock event for tool initialization."""
    event = Mock()
    event.company_id = "test_company"
    event.user_id = "test_user"
    event.payload.chat_id = "test_chat"
    event.payload.assistant_message = Mock(id="test_message")
    return event
