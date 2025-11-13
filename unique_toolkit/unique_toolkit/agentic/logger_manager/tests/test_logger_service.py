"""
Tests for MessageStepLogger service.

This file demonstrates how to use the MessageStepLogger class for tracking
message steps in agentic tools.
"""

from unittest.mock import patch

import pytest

from unique_toolkit.agentic.logger_manager.service import MessageStepLogger
from unique_toolkit.app import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogEvent,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentChunk


# Centralized Fixtures
@pytest.fixture
def test_event() -> ChatEvent:
    """
    Purpose: Provide a test ChatEvent for logger initialization.
    Why this matters: Consistent event structure ensures predictable test behavior.
    Setup summary: Creates event with test user, company, chat, and assistant IDs.
    """
    return ChatEvent(
        id="some-id",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id="test_user",
        company_id="test_company",
        payload=ChatEventPayload(
            assistant_id="test_assistant",
            chat_id="test_chat",
            name="module",
            description="module_description",
            configuration={},
            user_message=ChatEventUserMessage(
                id="user_message_id",
                text="Test user message",
                created_at="2021-01-01T00:00:00Z",
                language="DE",
                original_text="Test user message",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="assistant_message_id", created_at="2021-01-01T00:00:00Z"
            ),
            metadata_filter={},
        ),
    )


@pytest.fixture
def chat_service(test_event: ChatEvent) -> ChatService:
    """
    Purpose: Provide a ChatService instance for logger tests.
    Why this matters: Logger requires ChatService for message log operations.
    Setup summary: Creates ChatService with test event.
    """
    return ChatService(test_event)


@pytest.fixture
def logger(chat_service: ChatService, test_event: ChatEvent) -> MessageStepLogger:
    """
    Purpose: Provide a MessageStepLogger instance for testing.
    Why this matters: Centralized logger creation ensures consistent test setup.
    Setup summary: Creates MessageStepLogger with chat service and event.
    """
    return MessageStepLogger(chat_service, test_event)


@pytest.fixture(autouse=True)
def reset_message_order_counters():
    """
    Purpose: Reset message order counters before each test.
    Why this matters: Prevents test interference from shared module-level state.
    Setup summary: Clear the _request_counters dictionary before each test.
    """
    from unique_toolkit.agentic.logger_manager.service import _request_counters
    
    # Clear counters before test
    _request_counters.clear()
    
    yield
    
    # Clear counters after test
    _request_counters.clear()


@pytest.fixture
def web_content_chunk() -> ContentChunk:
    """
    Purpose: Provide a web search content chunk for reference list tests.
    Why this matters: Ensures consistent test data for web search scenarios.
    Setup summary: Creates ContentChunk with URL and title for web search.
    """
    return ContentChunk(
        id="chunk_1",
        text="Content from web page 1",
        url="https://example.com/page1",
        title="Page 1 Title",
    )


@pytest.fixture
def internal_content_chunk_with_title() -> ContentChunk:
    """
    Purpose: Provide an internal content chunk with title for reference tests.
    Why this matters: Tests behavior when title is available for internal references.
    Setup summary: Creates ContentChunk with title and key for internal search.
    """
    return ContentChunk(
        id="chunk_internal_1",
        text="Internal document content",
        title="Internal Document Title",
        key="doc_key_1",
    )


@pytest.fixture
def internal_content_chunk_without_title() -> ContentChunk:
    """
    Purpose: Provide an internal content chunk without title for reference tests.
    Why this matters: Tests fallback behavior when title is missing.
    Setup summary: Creates ContentChunk with only key, no title.
    """
    return ContentChunk(
        id="chunk_internal_2",
        text="Another internal document",
        key="doc_key_2",
    )


# Initialization Tests
@pytest.mark.ai
def test_message_step_logger__initializes_chat_service__with_valid_event_AI(
    chat_service: ChatService, test_event: ChatEvent
) -> None:
    """
    Purpose: Verify MessageStepLogger stores chat service correctly.
    Why this matters: Chat service is required for all logging operations.
    Setup summary: Create logger with chat service and event, verify service is stored.
    """
    # Arrange
    # Act
    logger = MessageStepLogger(chat_service, test_event)

    # Assert
    assert isinstance(logger._chat_service, ChatService)
    assert logger._chat_service == chat_service


@pytest.mark.ai
def test_message_step_logger__initializes_event__with_valid_event_AI(
    chat_service: ChatService, test_event: ChatEvent
) -> None:
    """
    Purpose: Verify MessageStepLogger stores event correctly.
    Why this matters: Event contains message ID needed for logging operations.
    Setup summary: Create logger with chat service and event, verify event is stored.
    """
    # Arrange
    # Act
    logger = MessageStepLogger(chat_service, test_event)

    # Assert
    assert logger._event == test_event
    assert logger._event.payload.assistant_message.id == "assistant_message_id"


# Message Order Tests
@pytest.mark.ai
def test_get_next_message_order__returns_one__on_first_call_AI() -> None:
    """
    Purpose: Verify message order counter starts at 1 for new message ID.
    Why this matters: First log entry must have order 1 for proper sequencing.
    Setup summary: Call get_next_message_order with new message ID, verify returns 1.
    """
    # Arrange
    message_id = "test_message_first"

    # Act
    order = MessageStepLogger.get_next_message_order(message_id)

    # Assert
    assert isinstance(order, int)
    assert order == 1


@pytest.mark.ai
def test_get_next_message_order__increments_counter__on_subsequent_calls_AI() -> None:
    """
    Purpose: Verify message order counter increments for same message ID.
    Why this matters: Sequential log entries must have increasing order numbers.
    Setup summary: Call get_next_message_order twice with same message ID, verify increment.
    """
    # Arrange
    message_id = "test_message_increment"
    MessageStepLogger.get_next_message_order(message_id)  # First call

    # Act
    order = MessageStepLogger.get_next_message_order(message_id)

    # Assert
    assert isinstance(order, int)
    assert order == 2


@pytest.mark.ai
def test_get_next_message_order__starts_from_one__with_different_message_id_AI() -> None:
    """
    Purpose: Verify message order counter is independent per message ID.
    Why this matters: Each message should have its own independent order sequence.
    Setup summary: Call get_next_message_order with different message ID, verify starts at 1.
    """
    # Arrange
    first_message_id = "test_message_one"
    MessageStepLogger.get_next_message_order(first_message_id)  # Increment first
    different_message_id = "test_message_two"

    # Act
    order = MessageStepLogger.get_next_message_order(different_message_id)

    # Assert
    assert isinstance(order, int)
    assert order == 1


# Static Method Tests
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_correct_message_id_AI(
    mock_create_message_log, chat_service: ChatService
) -> None:
    """
    Purpose: Verify create_message_log_entry passes message_id to chat service.
    Why this matters: Message ID is required to associate log with correct message.
    Setup summary: Mock chat service, call create_message_log_entry, verify message_id parameter.
    """
    # Arrange
    message_id = "test_message_123"
    text = "Processing search query..."

    # Act
    MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text=text,
        status=MessageLogStatus.RUNNING,
    )

    # Assert
    mock_create_message_log.assert_called_once()
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["message_id"], str)
    assert call_args.kwargs["message_id"] == message_id


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_correct_text_AI(
    mock_create_message_log, chat_service: ChatService
) -> None:
    """
    Purpose: Verify create_message_log_entry passes text to chat service.
    Why this matters: Text content is displayed to users in message logs.
    Setup summary: Mock chat service, call create_message_log_entry, verify text parameter.
    """
    # Arrange
    message_id = "test_message_123"
    text = "Processing search query..."

    # Act
    MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text=text,
        status=MessageLogStatus.RUNNING,
    )

    # Assert
    mock_create_message_log.assert_called_once()
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["text"], str)
    assert call_args.kwargs["text"] == text


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_correct_status_AI(
    mock_create_message_log, chat_service: ChatService
) -> None:
    """
    Purpose: Verify create_message_log_entry passes status to chat service.
    Why this matters: Status indicates log entry state (RUNNING, COMPLETED, etc.).
    Setup summary: Mock chat service, call create_message_log_entry, verify status parameter.
    """
    # Arrange
    message_id = "test_message_123"
    status = MessageLogStatus.RUNNING

    # Act
    MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text="Test text",
        status=status,
    )

    # Assert
    mock_create_message_log.assert_called_once()
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["status"], MessageLogStatus)
    assert call_args.kwargs["status"] == status


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_custom_details_AI(
    mock_create_message_log, chat_service: ChatService
) -> None:
    """
    Purpose: Verify create_message_log_entry passes custom details to chat service.
    Why this matters: Details provide additional context about log entry events.
    Setup summary: Mock chat service, create custom details, call create_message_log_entry, verify details parameter.
    """
    # Arrange
    message_id = "test_message_123"
    custom_details = MessageLogDetails(
        data=[MessageLogEvent(type="WebSearch", text="Custom event text")]
    )

    # Act
    MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text="Custom log entry",
        status=MessageLogStatus.RUNNING,
        details=custom_details,
    )

    # Assert
    mock_create_message_log.assert_called_once()
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["details"], MessageLogDetails)
    assert call_args.kwargs["details"] == custom_details


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_custom_references_AI(
    mock_create_message_log, chat_service: ChatService
) -> None:
    """
    Purpose: Verify create_message_log_entry passes custom references to chat service.
    Why this matters: References link log entries to source content chunks.
    Setup summary: Mock chat service, create custom references, call create_message_log_entry, verify references parameter.
    """
    # Arrange
    message_id = "test_message_123"
    custom_refs = MessageLogUncitedReferences(data=[])

    # Act
    MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text="Custom log entry",
        status=MessageLogStatus.RUNNING,
        uncited_references=custom_refs,
    )

    # Assert
    mock_create_message_log.assert_called_once()
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["uncited_references"], MessageLogUncitedReferences)
    assert call_args.kwargs["uncited_references"] == custom_refs


# Instance Method Tests
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_write_message_log_text_message__calls_chat_service__with_text_AI(
    mock_create_message_log, logger: MessageStepLogger, test_event: ChatEvent
) -> None:
    """
    Purpose: Verify write_message_log_text_message passes text to chat service.
    Why this matters: Text content is displayed to users in progress logs.
    Setup summary: Mock chat service, call write_message_log_text_message, verify text parameter.
    """
    # Arrange
    text = "Starting web search..."

    # Act
    logger.write_message_log_text_message(text)

    # Assert
    mock_create_message_log.assert_called_once()
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["text"], str)
    assert call_args.kwargs["text"] == text


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_write_message_log_text_message__calls_chat_service__with_completed_status_AI(
    mock_create_message_log, logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify write_message_log_text_message uses COMPLETED status.
    Why this matters: Text messages indicate completed steps, not in-progress operations.
    Setup summary: Mock chat service, call write_message_log_text_message, verify status is COMPLETED.
    """
    # Arrange

    # Act
    logger.write_message_log_text_message("Test message")

    # Assert
    mock_create_message_log.assert_called_once()
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["status"], MessageLogStatus)
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_write_message_log_text_message__calls_chat_service__with_message_id_AI(
    mock_create_message_log, logger: MessageStepLogger, test_event: ChatEvent
) -> None:
    """
    Purpose: Verify write_message_log_text_message uses event message ID.
    Why this matters: Log entries must be associated with correct assistant message.
    Setup summary: Mock chat service, call write_message_log_text_message, verify message_id from event.
    """
    # Arrange

    # Act
    logger.write_message_log_text_message("Test message")

    # Assert
    mock_create_message_log.assert_called_once()
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["message_id"], str)
    assert call_args.kwargs["message_id"] == test_event.payload.assistant_message.id


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_write_message_log_text_message__increments_order__on_multiple_calls_AI(
    mock_create_message_log, logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify write_message_log_text_message increments order on multiple calls.
    Why this matters: Sequential log entries must have increasing order numbers.
    Setup summary: Mock chat service, call write_message_log_text_message three times, verify order increments.
    """
    # Arrange

    # Act
    logger.write_message_log_text_message("Step 1")
    logger.write_message_log_text_message("Step 2")
    logger.write_message_log_text_message("Step 3")

    # Assert
    assert mock_create_message_log.call_count == 3
    calls = mock_create_message_log.call_args_list
    assert isinstance(calls[0].kwargs["order"], int)
    assert calls[0].kwargs["order"] == 1
    assert isinstance(calls[1].kwargs["order"], int)
    assert calls[1].kwargs["order"] == 2
    assert isinstance(calls[2].kwargs["order"], int)
    assert calls[2].kwargs["order"] == 3


# Reference List Tests - Web Search
@pytest.mark.ai
def test_define_reference_list__returns_list__with_web_search_chunks_AI(
    web_content_chunk: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list returns list of references for web search.
    Why this matters: References link log entries to web search result URLs.
    Setup summary: Create web content chunk, call define_reference_list, verify returns list.
    """
    # Arrange
    content_chunks = [web_content_chunk]

    # Act
    references = MessageStepLogger.define_reference_list(
        source="web_search", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references, list)
    assert len(references) == 1


@pytest.mark.ai
def test_define_reference_list__sets_sequence_number__for_first_chunk_AI(
    web_content_chunk: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list sets sequence_number to 1 for first chunk.
    Why this matters: Sequence numbers order references in display.
    Setup summary: Create web content chunk, call define_reference_list, verify first reference sequence_number is 1.
    """
    # Arrange
    content_chunks = [web_content_chunk]

    # Act
    references = MessageStepLogger.define_reference_list(
        source="web_search", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].sequence_number, int)
    assert references[0].sequence_number == 1


@pytest.mark.ai
def test_define_reference_list__sets_url__from_chunk_url_AI(
    web_content_chunk: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list sets URL from chunk URL.
    Why this matters: URL links reference to source web page.
    Setup summary: Create web content chunk with URL, call define_reference_list, verify reference URL matches.
    """
    # Arrange
    content_chunks = [web_content_chunk]

    # Act
    references = MessageStepLogger.define_reference_list(
        source="web_search", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].url, str)
    assert references[0].url == "https://example.com/page1"


@pytest.mark.ai
def test_define_reference_list__sets_source__from_parameter_AI(
    web_content_chunk: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list sets source from parameter.
    Why this matters: Source identifies where reference content originated.
    Setup summary: Create web content chunk, call define_reference_list with source, verify reference source matches.
    """
    # Arrange
    content_chunks = [web_content_chunk]
    source = "web_search"

    # Act
    references = MessageStepLogger.define_reference_list(
        source=source, content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].source, str)
    assert references[0].source == source


@pytest.mark.ai
def test_define_reference_list__sets_name__from_chunk_url_AI(
    web_content_chunk: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list sets name from chunk URL.
    Why this matters: Name is displayed to users as reference identifier.
    Setup summary: Create web content chunk with URL, call define_reference_list, verify reference name is URL.
    """
    # Arrange
    content_chunks = [web_content_chunk]

    # Act
    references = MessageStepLogger.define_reference_list(
        source="web_search", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].name, str)
    assert references[0].name == "https://example.com/page1"


@pytest.mark.ai
def test_define_reference_list__increments_sequence_number__for_multiple_chunks_AI() -> None:
    """
    Purpose: Verify define_reference_list increments sequence_number for multiple chunks.
    Why this matters: Multiple references must be ordered correctly.
    Setup summary: Create two web content chunks, call define_reference_list, verify sequence numbers increment.
    """
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

    # Act
    references = MessageStepLogger.define_reference_list(
        source="web_search", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].sequence_number, int)
    assert references[0].sequence_number == 1
    assert isinstance(references[1].sequence_number, int)
    assert references[1].sequence_number == 2


# Reference List Tests - Internal Search
@pytest.mark.ai
def test_define_reference_list_for_internal__returns_list__with_internal_chunks_AI(
    internal_content_chunk_with_title: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list_for_internal returns list of references.
    Why this matters: References link log entries to internal document sources.
    Setup summary: Create internal content chunk, call define_reference_list_for_internal, verify returns list.
    """
    # Arrange
    content_chunks = [internal_content_chunk_with_title]

    # Act
    references = MessageStepLogger.define_reference_list_for_internal(
        source="internal", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references, list)
    assert len(references) == 1


@pytest.mark.ai
def test_define_reference_list_for_internal__sets_sequence_number__for_first_chunk_AI(
    internal_content_chunk_with_title: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list_for_internal sets sequence_number to 1.
    Why this matters: Sequence numbers order references in display.
    Setup summary: Create internal content chunk, call define_reference_list_for_internal, verify sequence_number is 1.
    """
    # Arrange
    content_chunks = [internal_content_chunk_with_title]

    # Act
    references = MessageStepLogger.define_reference_list_for_internal(
        source="internal", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].sequence_number, int)
    assert references[0].sequence_number == 1


@pytest.mark.ai
def test_define_reference_list_for_internal__sets_source_id__from_chunk_id_AI(
    internal_content_chunk_with_title: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list_for_internal sets source_id from chunk ID.
    Why this matters: Source ID identifies the internal document chunk.
    Setup summary: Create internal content chunk with ID, call define_reference_list_for_internal, verify source_id matches.
    """
    # Arrange
    content_chunks = [internal_content_chunk_with_title]

    # Act
    references = MessageStepLogger.define_reference_list_for_internal(
        source="internal", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].source_id, str)
    assert references[0].source_id == "chunk_internal_1"


@pytest.mark.ai
def test_define_reference_list_for_internal__sets_name__from_chunk_title_AI(
    internal_content_chunk_with_title: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list_for_internal uses title when available.
    Why this matters: Title provides meaningful name for internal document references.
    Setup summary: Create internal content chunk with title, call define_reference_list_for_internal, verify name is title.
    """
    # Arrange
    content_chunks = [internal_content_chunk_with_title]

    # Act
    references = MessageStepLogger.define_reference_list_for_internal(
        source="internal", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].name, str)
    assert references[0].name == "Internal Document Title"


@pytest.mark.ai
def test_define_reference_list_for_internal__sets_name__from_chunk_key_when_no_title_AI(
    internal_content_chunk_without_title: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list_for_internal falls back to key when title missing.
    Why this matters: References need names even when title is unavailable.
    Setup summary: Create internal content chunk without title, call define_reference_list_for_internal, verify name is key.
    """
    # Arrange
    content_chunks = [internal_content_chunk_without_title]

    # Act
    references = MessageStepLogger.define_reference_list_for_internal(
        source="internal", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].name, str)
    assert references[0].name == "doc_key_2"


@pytest.mark.ai
def test_define_reference_list_for_internal__sets_empty_url__for_internal_chunks_AI(
    internal_content_chunk_with_title: ContentChunk,
) -> None:
    """
    Purpose: Verify define_reference_list_for_internal sets empty URL for internal chunks.
    Why this matters: Internal documents don't have URLs, only source IDs.
    Setup summary: Create internal content chunk, call define_reference_list_for_internal, verify URL is empty string.
    """
    # Arrange
    content_chunks = [internal_content_chunk_with_title]

    # Act
    references = MessageStepLogger.define_reference_list_for_internal(
        source="internal", content_chunks=content_chunks
    )

    # Assert
    assert isinstance(references[0].url, str)
    assert references[0].url == ""


# Full Message Tests - Web Search
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_full_specific_message__calls_chat_service__with_web_search_AI(
    mock_create_message_log, logger: MessageStepLogger, web_content_chunk: ContentChunk
) -> None:
    """
    Purpose: Verify create_full_specific_message calls chat service for web search.
    Why this matters: Full messages create complete log entries with question and results.
    Setup summary: Mock chat service, call create_full_specific_message with web search, verify service called.
    """
    # Arrange
    message = "What is machine learning?"
    content_chunks = [web_content_chunk]

    # Act
    logger.create_full_specific_message(
        message=message,
        source="web",
        search_type="WebSearch",
        content_chunks=content_chunks,
    )

    # Assert
    mock_create_message_log.assert_called_once()


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_full_specific_message__includes_question__in_text_for_web_search_AI(
    mock_create_message_log, logger: MessageStepLogger, web_content_chunk: ContentChunk
) -> None:
    """
    Purpose: Verify create_full_specific_message includes question in text.
    Why this matters: Users need to see what question was asked in the log.
    Setup summary: Mock chat service, call create_full_specific_message, verify text contains question marker and message.
    """
    # Arrange
    message = "What is machine learning?"
    content_chunks = [web_content_chunk]

    # Act
    logger.create_full_specific_message(
        message=message,
        source="web",
        search_type="WebSearch",
        content_chunks=content_chunks,
    )

    # Assert
    call_args = mock_create_message_log.call_args
    text = call_args.kwargs["text"]
    assert isinstance(text, str)
    assert "**Question asked**" in text
    assert message in text


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_full_specific_message__includes_hits_marker__in_text_for_web_search_AI(
    mock_create_message_log, logger: MessageStepLogger, web_content_chunk: ContentChunk
) -> None:
    """
    Purpose: Verify create_full_specific_message includes hits marker in text.
    Why this matters: Hits marker indicates search results section in log.
    Setup summary: Mock chat service, call create_full_specific_message, verify text contains hits marker.
    """
    # Arrange
    content_chunks = [web_content_chunk]

    # Act
    logger.create_full_specific_message(
        message="Test question",
        source="web",
        search_type="WebSearch",
        content_chunks=content_chunks,
    )

    # Assert
    call_args = mock_create_message_log.call_args
    text = call_args.kwargs["text"]
    assert isinstance(text, str)
    assert "**Found hits**" in text


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_full_specific_message__sets_completed_status__for_web_search_AI(
    mock_create_message_log, logger: MessageStepLogger, web_content_chunk: ContentChunk
) -> None:
    """
    Purpose: Verify create_full_specific_message uses COMPLETED status for web search.
    Why this matters: Completed status indicates search operation finished successfully.
    Setup summary: Mock chat service, call create_full_specific_message, verify status is COMPLETED.
    """
    # Arrange
    content_chunks = [web_content_chunk]

    # Act
    logger.create_full_specific_message(
        message="Test question",
        source="web",
        search_type="WebSearch",
        content_chunks=content_chunks,
    )

    # Assert
    call_args = mock_create_message_log.call_args
    assert isinstance(call_args.kwargs["status"], MessageLogStatus)
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_full_specific_message__creates_web_search_details__for_web_search_AI(
    mock_create_message_log, logger: MessageStepLogger, web_content_chunk: ContentChunk
) -> None:
    """
    Purpose: Verify create_full_specific_message creates WebSearch details.
    Why this matters: Details identify the type of search operation performed.
    Setup summary: Mock chat service, call create_full_specific_message with WebSearch, verify details type.
    """
    # Arrange
    content_chunks = [web_content_chunk]

    # Act
    logger.create_full_specific_message(
        message="Test question",
        source="web",
        search_type="WebSearch",
        content_chunks=content_chunks,
    )

    # Assert
    call_args = mock_create_message_log.call_args
    details = call_args.kwargs["details"]
    assert isinstance(details, MessageLogDetails)
    assert len(details.data) == 1
    assert isinstance(details.data[0].type, str)
    assert details.data[0].type == "WebSearch"


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_full_specific_message__creates_references__for_web_search_AI(
    mock_create_message_log, logger: MessageStepLogger, web_content_chunk: ContentChunk
) -> None:
    """
    Purpose: Verify create_full_specific_message creates references for web search.
    Why this matters: References link log entries to source web pages.
    Setup summary: Mock chat service, call create_full_specific_message, verify uncited_references created.
    """
    # Arrange
    content_chunks = [web_content_chunk]

    # Act
    logger.create_full_specific_message(
        message="Test question",
        source="web",
        search_type="WebSearch",
        content_chunks=content_chunks,
    )

    # Assert
    call_args = mock_create_message_log.call_args
    uncited_refs = call_args.kwargs["uncited_references"]
    assert isinstance(uncited_refs, MessageLogUncitedReferences)
    assert len(uncited_refs.data) == 1


# Full Message Tests - Internal Search
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_full_specific_message__creates_internal_search_details__for_internal_search_AI(
    mock_create_message_log, logger: MessageStepLogger, internal_content_chunk_with_title: ContentChunk
) -> None:
    """
    Purpose: Verify create_full_specific_message creates InternalSearch details.
    Why this matters: Details identify the type of search operation performed.
    Setup summary: Mock chat service, call create_full_specific_message with InternalSearch, verify details type.
    """
    # Arrange
    content_chunks = [internal_content_chunk_with_title]

    # Act
    logger.create_full_specific_message(
        message="Find company policies",
        source="internal",
        search_type="InternalSearch",
        content_chunks=content_chunks,
    )

    # Assert
    call_args = mock_create_message_log.call_args
    details = call_args.kwargs["details"]
    assert isinstance(details, MessageLogDetails)
    assert len(details.data) == 1
    assert isinstance(details.data[0].type, str)
    assert details.data[0].type == "InternalSearch"


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_full_specific_message__creates_references__for_internal_search_AI(
    mock_create_message_log, logger: MessageStepLogger, internal_content_chunk_with_title: ContentChunk
) -> None:
    """
    Purpose: Verify create_full_specific_message creates references for internal search.
    Why this matters: References link log entries to internal document sources.
    Setup summary: Mock chat service, call create_full_specific_message, verify uncited_references created with internal format.
    """
    # Arrange
    content_chunks = [internal_content_chunk_with_title]

    # Act
    logger.create_full_specific_message(
        message="Find company policies",
        source="internal",
        search_type="InternalSearch",
        content_chunks=content_chunks,
    )

    # Assert
    call_args = mock_create_message_log.call_args
    uncited_refs = call_args.kwargs["uncited_references"]
    assert isinstance(uncited_refs, MessageLogUncitedReferences)
    assert len(uncited_refs.data) == 1
    assert isinstance(uncited_refs.data[0].name, str)
    assert uncited_refs.data[0].name == "Internal Document Title"
    assert isinstance(uncited_refs.data[0].url, str)
    assert uncited_refs.data[0].url == ""
