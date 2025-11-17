"""
Tests for MessageStepLogger service.

This file demonstrates how to use the MessageStepLogger class for tracking
message steps in agentic tools.
"""

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from unittest.mock import Mock

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
from unique_toolkit.content.schemas import ContentReference


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
    from unique_toolkit.agentic.logger_manager.service import (
        _request_counters,  # type: ignore[attr-defined]
    )

    # Clear counters before test
    _request_counters.clear()

    yield

    # Clear counters after test
    _request_counters.clear()


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
    assert isinstance(logger._chat_service, ChatService)  # type: ignore[attr-defined]
    assert logger._chat_service == chat_service  # type: ignore[attr-defined]


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
    assert logger._event == test_event  # type: ignore[attr-defined]
    assert logger._event.payload.assistant_message.id == "assistant_message_id"  # type: ignore[attr-defined]


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
    order = MessageStepLogger.get_next_message_order(message_id=message_id)

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
    _ = MessageStepLogger.get_next_message_order(message_id=message_id)  # First call

    # Act
    order = MessageStepLogger.get_next_message_order(message_id=message_id)

    # Assert
    assert isinstance(order, int)
    assert order == 2


@pytest.mark.ai
def test_get_next_message_order__starts_from_one__with_different_message_id_AI() -> (
    None
):
    """
    Purpose: Verify message order counter is independent per message ID.
    Why this matters: Each message should have its own independent order sequence.
    Setup summary: Call get_next_message_order with different message ID, verify starts at 1.
    """
    # Arrange
    first_message_id = "test_message_one"
    _ = MessageStepLogger.get_next_message_order(
        message_id=first_message_id
    )  # Increment first
    different_message_id = "test_message_two"

    # Act
    order = MessageStepLogger.get_next_message_order(message_id=different_message_id)

    # Assert
    assert isinstance(order, int)
    assert order == 1


# Static Method Tests
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_correct_message_id_AI(
    mock_create_message_log: "Mock", chat_service: ChatService
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
    _ = MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text=text,
        status=MessageLogStatus.RUNNING,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["message_id"], str)  # type: ignore[attr-defined]
    assert call_args.kwargs["message_id"] == message_id  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_correct_text_AI(
    mock_create_message_log: "Mock", chat_service: ChatService
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
    _ = MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text=text,
        status=MessageLogStatus.RUNNING,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["text"], str)  # type: ignore[attr-defined]
    assert call_args.kwargs["text"] == text  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_correct_status_AI(
    mock_create_message_log: "Mock", chat_service: ChatService
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
    _ = MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text="Test text",
        status=status,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["status"], MessageLogStatus)  # type: ignore[attr-defined]
    assert call_args.kwargs["status"] == status  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_custom_details_AI(
    mock_create_message_log: "Mock", chat_service: ChatService
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
    _ = MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text="Custom log entry",
        status=MessageLogStatus.RUNNING,
        details=custom_details,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["details"], MessageLogDetails)  # type: ignore[attr-defined]
    assert call_args.kwargs["details"] == custom_details  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_custom_references_AI(
    mock_create_message_log: "Mock", chat_service: ChatService
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
    _ = MessageStepLogger.create_message_log_entry(
        chat_service=chat_service,
        message_id=message_id,
        text="Custom log entry",
        status=MessageLogStatus.RUNNING,
        uncited_references=custom_refs,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(
        call_args.kwargs["uncited_references"], MessageLogUncitedReferences
    )  # type: ignore[attr-defined]
    assert call_args.kwargs["uncited_references"] == custom_refs  # type: ignore[attr-defined]


# Instance Method Tests
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_write_message_log_text_message__calls_chat_service__with_text_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify write_message_log_text_message passes text to chat service.
    Why this matters: Text content is displayed to users in progress logs.
    Setup summary: Mock chat service, call write_message_log_text_message, verify text parameter.
    """
    # Arrange
    text = "Starting web search..."

    # Act
    _ = logger.write_message_log_text_message(text=text)

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["text"], str)  # type: ignore[attr-defined]
    assert call_args.kwargs["text"] == text  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_write_message_log_text_message__calls_chat_service__with_completed_status_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify write_message_log_text_message uses COMPLETED status.
    Why this matters: Text messages indicate completed steps, not in-progress operations.
    Setup summary: Mock chat service, call write_message_log_text_message, verify status is COMPLETED.
    """
    # Arrange

    # Act
    _ = logger.write_message_log_text_message(text="Test message")

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["status"], MessageLogStatus)  # type: ignore[attr-defined]
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_write_message_log_text_message__calls_chat_service__with_message_id_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger, test_event: ChatEvent
) -> None:
    """
    Purpose: Verify write_message_log_text_message uses event message ID.
    Why this matters: Log entries must be associated with correct assistant message.
    Setup summary: Mock chat service, call write_message_log_text_message, verify message_id from event.
    """
    # Arrange

    # Act
    _ = logger.write_message_log_text_message(text="Test message")

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["message_id"], str)  # type: ignore[attr-defined]
    assert call_args.kwargs["message_id"] == test_event.payload.assistant_message.id  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_write_message_log_text_message__increments_order__on_multiple_calls_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify write_message_log_text_message increments order on multiple calls.
    Why this matters: Sequential log entries must have increasing order numbers.
    Setup summary: Mock chat service, call write_message_log_text_message three times, verify order increments.
    """
    # Arrange

    # Act
    _ = logger.write_message_log_text_message(text="Step 1")
    _ = logger.write_message_log_text_message(text="Step 2")
    _ = logger.write_message_log_text_message(text="Step 3")

    # Assert
    assert mock_create_message_log.call_count == 3  # type: ignore[attr-defined]
    calls = mock_create_message_log.call_args_list  # type: ignore[attr-defined]
    assert isinstance(calls[0].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[0].kwargs["order"] == 1  # type: ignore[attr-defined]
    assert isinstance(calls[1].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[1].kwargs["order"] == 2  # type: ignore[attr-defined]
    assert isinstance(calls[2].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[2].kwargs["order"] == 3  # type: ignore[attr-defined]


# Full Message Tests - Web Search
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__calls_chat_service__with_web_search_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_post calls chat service for web search.
    Why this matters: Full messages create complete log entries with question and results.
    Setup summary: Mock chat service, call create_message_log_post with web search, verify service called.
    """
    # Arrange
    query_list = ["What is machine learning?"]
    data = []

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="WebSearch",
        data=data,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__includes_question__in_text_for_web_search_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_post includes question in text.
    Why this matters: Users need to see what question was asked in the log.
    Setup summary: Mock chat service, call create_message_log_post, verify text contains question marker and message.
    """
    # Arrange
    query_list = ["What is machine learning?"]
    data = []

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="WebSearch",
        data=data,
    )

    # Assert
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    text = call_args.kwargs["text"]  # type: ignore[attr-defined]
    assert isinstance(text, str)
    assert "**Web Search**" in text
    assert "What is machine learning?" in text


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__includes_web_search_marker__in_text_for_web_search_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_post includes web search marker in text.
    Why this matters: Web search marker indicates the type of search performed.
    Setup summary: Mock chat service, call create_message_log_post, verify text contains web search marker.
    """
    # Arrange
    query_list = ["Test question"]
    data = []

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="WebSearch",
        data=data,
    )

    # Assert
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    text = call_args.kwargs["text"]  # type: ignore[attr-defined]
    assert isinstance(text, str)
    assert "**Web Search**" in text


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__sets_completed_status__for_web_search_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_post uses COMPLETED status for web search.
    Why this matters: Completed status indicates search operation finished successfully.
    Setup summary: Mock chat service, call create_message_log_post, verify status is COMPLETED.
    """
    # Arrange
    query_list = ["Test question"]
    data = []

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="WebSearch",
        data=data,
    )

    # Assert
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["status"], MessageLogStatus)  # type: ignore[attr-defined]
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__creates_web_search_details__for_web_search_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_post creates WebSearch details.
    Why this matters: Details identify the type of search operation performed.
    Setup summary: Mock chat service, call create_message_log_post with WebSearch, verify details type.
    """
    # Arrange
    query_list = ["Test question"]
    data = []

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="WebSearch",
        data=data,
    )

    # Assert
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    details = call_args.kwargs["details"]  # type: ignore[attr-defined]
    assert isinstance(details, MessageLogDetails)
    assert details.data is not None
    assert len(details.data) == 1
    assert isinstance(details.data[0].type, str)
    assert details.data[0].type == "WebSearch"


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__creates_references__for_web_search_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_post creates references for web search.
    Why this matters: References link log entries to source web pages.
    Setup summary: Mock chat service, call create_message_log_post, verify uncited_references created.
    """
    # Arrange
    query_list = ["Test question"]
    data = [
        ContentReference(
            name="https://example.com/page1",
            sequence_number=0,
            source="web",
            url="https://example.com/page1",
            source_id="https://example.com/page1",
        )
    ]

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="WebSearch",
        data=data,
    )

    # Assert
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    uncited_refs = call_args.kwargs["uncited_references"]  # type: ignore[attr-defined]
    assert isinstance(uncited_refs, MessageLogUncitedReferences)
    assert len(uncited_refs.data) == 1
    # Also verify references parameter
    references = call_args.kwargs["references"]  # type: ignore[attr-defined]
    assert isinstance(references, list)
    assert len(references) == 1


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__uses_message_id__from_event_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger, test_event: ChatEvent
) -> None:
    """
    Purpose: Verify create_message_log_post uses message_id from event.
    Why this matters: Message ID is required to associate log with correct message.
    Setup summary: Mock chat service, call create_message_log_post, verify message_id parameter.
    """
    # Arrange
    query_list = ["Test question"]
    data = []

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="WebSearch",
        data=data,
    )

    # Assert
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["message_id"], str)  # type: ignore[attr-defined]
    assert call_args.kwargs["message_id"] == test_event.payload.assistant_message.id  # type: ignore[attr-defined]


# Full Message Tests - Internal Search
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__creates_internal_search_details__for_internal_search_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_post creates InternalSearch details.
    Why this matters: Details identify the type of search operation performed.
    Setup summary: Mock chat service, call create_message_log_post with InternalSearch, verify details type.
    """
    # Arrange
    query_list = ["Find company policies"]
    data = []

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="InternalSearch",
        data=data,
    )

    # Assert
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    details = call_args.kwargs["details"]  # type: ignore[attr-defined]
    assert isinstance(details, MessageLogDetails)
    assert details.data is not None
    assert len(details.data) == 1
    assert isinstance(details.data[0].type, str)
    assert details.data[0].type == "InternalSearch"


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_post__creates_references__for_internal_search_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_post creates references for internal search.
    Why this matters: References link log entries to internal document sources.
    Setup summary: Mock chat service, call create_message_log_post, verify uncited_references created with internal format.
    """
    # Arrange
    query_list = ["Find company policies"]
    data = [
        ContentReference(
            name="Internal Document Title",
            sequence_number=0,
            source="internal",
            url="",
            source_id="chunk_internal_1",
        )
    ]

    # Act
    logger.create_message_log_post(
        query_list=query_list,
        search_type="InternalSearch",
        data=data,
    )

    # Assert
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    uncited_refs = call_args.kwargs["uncited_references"]  # type: ignore[attr-defined]
    assert isinstance(uncited_refs, MessageLogUncitedReferences)
    assert len(uncited_refs.data) == 1
    assert isinstance(uncited_refs.data[0].name, str)
    assert uncited_refs.data[0].name == "Internal Document Title"
    assert isinstance(uncited_refs.data[0].url, str)
    assert uncited_refs.data[0].url == ""
    # Also verify references parameter
    references = call_args.kwargs["references"]  # type: ignore[attr-defined]
    assert isinstance(references, list)
    assert len(references) == 1
