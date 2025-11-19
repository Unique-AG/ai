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


# Instance Method Tests
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_correct_message_id_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger, test_event: ChatEvent
) -> None:
    """
    Purpose: Verify create_message_log_entry passes message_id to chat service.
    Why this matters: Message ID is required to associate log with correct message.
    Setup summary: Mock chat service, call create_message_log_entry, verify message_id parameter.
    """
    # Arrange
    text = "Processing search query..."
    data: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text=text,
        data=data,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["message_id"], str)  # type: ignore[attr-defined]
    assert call_args.kwargs["message_id"] == test_event.payload.assistant_message.id  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_correct_text_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_entry passes text to chat service.
    Why this matters: Text content is displayed to users in message logs.
    Setup summary: Mock chat service, call create_message_log_entry, verify text parameter.
    """
    # Arrange
    text = "Processing search query..."
    data: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text=text,
        data=data,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["text"], str)  # type: ignore[attr-defined]
    assert call_args.kwargs["text"] == text  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_completed_status_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_entry uses COMPLETED status.
    Why this matters: Status indicates log entry state (COMPLETED).
    Setup summary: Mock chat service, call create_message_log_entry, verify status parameter.
    """
    # Arrange
    data: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text="Test text",
        data=data,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["status"], MessageLogStatus)  # type: ignore[attr-defined]
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_custom_details_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_entry passes custom details to chat service.
    Why this matters: Details provide additional context about log entry events.
    Setup summary: Mock chat service, create custom details, call create_message_log_entry, verify details parameter.
    """
    # Arrange
    custom_details = MessageLogDetails(
        data=[MessageLogEvent(type="WebSearch", text="Custom event text")]
    )
    data: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text="Custom log entry",
        details=custom_details,
        data=data,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["details"], MessageLogDetails)  # type: ignore[attr-defined]
    assert call_args.kwargs["details"] == custom_details  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_references_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_entry passes references to chat service.
    Why this matters: References link log entries to source content chunks.
    Setup summary: Mock chat service, create references, call create_message_log_entry, verify references parameter.
    """
    # Arrange
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
    logger.create_message_log_entry(
        text="Custom log entry",
        data=data,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["references"], list)  # type: ignore[attr-defined]
    assert len(call_args.kwargs["references"]) == 1  # type: ignore[attr-defined]
    assert isinstance(
        call_args.kwargs["uncited_references"], MessageLogUncitedReferences
    )  # type: ignore[attr-defined]
    assert len(call_args.kwargs["uncited_references"].data) == 1  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__increments_order__on_multiple_calls_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_entry increments order on multiple calls.
    Why this matters: Sequential log entries must have increasing order numbers.
    Setup summary: Mock chat service, call create_message_log_entry three times, verify order increments.
    """
    # Arrange
    data: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(text="Step 1", data=data)
    logger.create_message_log_entry(text="Step 2", data=data)
    logger.create_message_log_entry(text="Step 3", data=data)

    # Assert
    assert mock_create_message_log.call_count == 3  # type: ignore[attr-defined]
    calls = mock_create_message_log.call_args_list  # type: ignore[attr-defined]
    assert isinstance(calls[0].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[0].kwargs["order"] == 1  # type: ignore[attr-defined]
    assert isinstance(calls[1].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[1].kwargs["order"] == 2  # type: ignore[attr-defined]
    assert isinstance(calls[2].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[2].kwargs["order"] == 3  # type: ignore[attr-defined]
