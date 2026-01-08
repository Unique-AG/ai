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

from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.app import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.chat.schemas import (
    MessageLog,
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
def logger(chat_service: ChatService) -> MessageStepLogger:
    """
    Purpose: Provide a MessageStepLogger instance for testing.
    Why this matters: Centralized logger creation ensures consistent test setup.
    Setup summary: Creates MessageStepLogger with chat service.
    """
    return MessageStepLogger(chat_service)


@pytest.fixture(autouse=True)
def reset_message_order_counters():
    """
    Purpose: Reset message order counters before each test.
    Why this matters: Prevents test interference from shared module-level state.
    Setup summary: Clear the _request_counters dictionary before each test.
    """
    from unique_toolkit.agentic.message_log_manager.service import (
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
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify MessageStepLogger stores chat service correctly.
    Why this matters: Chat service is required for all logging operations.
    Setup summary: Create logger with chat service, verify service is stored.
    """
    # Arrange
    # Act
    logger = MessageStepLogger(chat_service)

    # Assert
    assert isinstance(logger._chat_service, ChatService)  # type: ignore[attr-defined]
    assert logger._chat_service == chat_service  # type: ignore[attr-defined]


@pytest.mark.ai
def test_message_step_logger__uses_chat_service_message_id__with_valid_event_AI(
    chat_service: ChatService, test_event: ChatEvent
) -> None:
    """
    Purpose: Verify MessageStepLogger uses chat service message ID correctly.
    Why this matters: Message ID is needed for logging operations.
    Setup summary: Create logger with chat service, verify it uses chat service's message ID.
    """
    # Arrange
    # Act
    logger = MessageStepLogger(chat_service)

    # Assert
    assert (
        logger._chat_service._assistant_message_id
        == test_event.payload.assistant_message.id
    )  # type: ignore[attr-defined]


# Message Order Tests
@pytest.mark.ai
def test_get_next_message_order__returns_one__on_first_call_AI(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify message order counter starts at 1 for new message ID.
    Why this matters: First log entry must have order 1 for proper sequencing.
    Setup summary: Create logger, call _get_next_message_order with new message ID, verify returns 1.
    """
    # Arrange
    logger = MessageStepLogger(chat_service)
    message_id = "test_message_first"

    # Act
    order = logger._get_next_message_order(message_id=message_id)  # type: ignore[attr-defined]

    # Assert
    assert isinstance(order, int)
    assert order == 1


@pytest.mark.ai
def test_get_next_message_order__increments_counter__on_subsequent_calls_AI(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify message order counter increments for same message ID.
    Why this matters: Sequential log entries must have increasing order numbers.
    Setup summary: Create logger, call _get_next_message_order twice with same message ID, verify increment.
    """
    # Arrange
    logger = MessageStepLogger(chat_service)
    message_id = "test_message_increment"
    _ = logger._get_next_message_order(message_id=message_id)  # type: ignore[attr-defined]  # First call

    # Act
    order = logger._get_next_message_order(message_id=message_id)  # type: ignore[attr-defined]

    # Assert
    assert isinstance(order, int)
    assert order == 2


@pytest.mark.ai
def test_get_next_message_order__starts_from_one__with_different_message_id_AI(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify message order counter is independent per message ID.
    Why this matters: Each message should have its own independent order sequence.
    Setup summary: Create logger, call _get_next_message_order with different message ID, verify starts at 1.
    """
    # Arrange
    logger = MessageStepLogger(chat_service)
    first_message_id = "test_message_one"
    _ = logger._get_next_message_order(message_id=first_message_id)  # type: ignore[attr-defined]  # Increment first
    different_message_id = "test_message_two"

    # Act
    order = logger._get_next_message_order(message_id=different_message_id)  # type: ignore[attr-defined]

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
    references: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text=text,
        references=references,
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
    references: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text=text,
        references=references,
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
    references: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text="Test text",
        references=references,
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
    references: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text="Custom log entry",
        details=custom_details,
        references=references,
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
    references = [
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
        references=references,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(call_args.kwargs["references"], list)  # type: ignore[attr-defined]
    assert len(call_args.kwargs["references"]) == 0  # type: ignore[attr-defined]  # references is always empty, actual refs go to uncited_references
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
    references: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(text="Step 1", references=references)
    logger.create_message_log_entry(text="Step 2", references=references)
    logger.create_message_log_entry(text="Step 3", references=references)

    # Assert
    assert mock_create_message_log.call_count == 3  # type: ignore[attr-defined]
    calls = mock_create_message_log.call_args_list  # type: ignore[attr-defined]
    assert isinstance(calls[0].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[0].kwargs["order"] == 1  # type: ignore[attr-defined]
    assert isinstance(calls[1].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[1].kwargs["order"] == 2  # type: ignore[attr-defined]
    assert isinstance(calls[2].kwargs["order"], int)  # type: ignore[attr-defined]
    assert calls[2].kwargs["order"] == 3  # type: ignore[attr-defined]


@pytest.mark.ai
def test_create_message_log_entry__returns_none__when_assistant_message_id_not_set_AI(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify create_message_log_entry returns None when assistant_message_id is not set.
    Why this matters: Operation should fail gracefully when message context is missing.
    Setup summary: Create logger with chat service that has no assistant_message_id, verify returns None.
    """
    # Arrange
    chat_service._assistant_message_id = ""  # Empty string is falsy
    logger = MessageStepLogger(chat_service)

    # Act
    result = logger.create_message_log_entry(
        text="Test text",
        references=[],
    )

    # Assert
    assert result is None


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_message_log_entry__calls_chat_service__with_custom_status_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_message_log_entry passes custom status to chat service.
    Why this matters: Status can be customized for different log entry states.
    Setup summary: Mock chat service, call create_message_log_entry with RUNNING status, verify status parameter.
    """
    # Arrange
    references: list[ContentReference] = []

    # Act
    logger.create_message_log_entry(
        text="Test text",
        status=MessageLogStatus.RUNNING,
        references=references,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["status"] == MessageLogStatus.RUNNING  # type: ignore[attr-defined]


# Update Message Log Entry Tests
@pytest.fixture
def sample_message_log() -> MessageLog:
    """
    Purpose: Provide a sample MessageLog for update tests.
    Why this matters: Update tests require an existing message log.
    Setup summary: Creates MessageLog with test data.
    """
    return MessageLog(
        message_log_id="test_message_log_id",
        message_id="assistant_message_id",
        status=MessageLogStatus.RUNNING,
        text="Initial text",
        order=1,
        references=[],
    )


@pytest.mark.ai
@patch.object(ChatService, "update_message_log", spec=True)
def test_update_message_log_entry__calls_chat_service__with_correct_message_log_id_AI(
    mock_update_message_log: "Mock",
    logger: MessageStepLogger,
    sample_message_log: MessageLog,
) -> None:
    """
    Purpose: Verify update_message_log_entry passes message_log_id to chat service.
    Why this matters: Message log ID is required to identify which log to update.
    Setup summary: Mock chat service, call update_message_log_entry, verify message_log_id parameter.
    """
    # Arrange
    # Act
    logger.update_message_log_entry(
        message_log=sample_message_log,
        status=MessageLogStatus.COMPLETED,
        references=[],
    )

    # Assert
    mock_update_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_update_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["message_log_id"] == "test_message_log_id"  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "update_message_log", spec=True)
def test_update_message_log_entry__calls_chat_service__with_correct_order_AI(
    mock_update_message_log: "Mock",
    logger: MessageStepLogger,
    sample_message_log: MessageLog,
) -> None:
    """
    Purpose: Verify update_message_log_entry preserves order from original message log.
    Why this matters: Order must be preserved during updates to maintain sequence.
    Setup summary: Mock chat service, call update_message_log_entry, verify order parameter.
    """
    # Arrange
    # Act
    logger.update_message_log_entry(
        message_log=sample_message_log,
        status=MessageLogStatus.COMPLETED,
        references=[],
    )

    # Assert
    mock_update_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_update_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["order"] == 1  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "update_message_log", spec=True)
def test_update_message_log_entry__calls_chat_service__with_correct_status_AI(
    mock_update_message_log: "Mock",
    logger: MessageStepLogger,
    sample_message_log: MessageLog,
) -> None:
    """
    Purpose: Verify update_message_log_entry passes status to chat service.
    Why this matters: Status indicates the updated state of the log entry.
    Setup summary: Mock chat service, call update_message_log_entry, verify status parameter.
    """
    # Arrange
    # Act
    logger.update_message_log_entry(
        message_log=sample_message_log,
        status=MessageLogStatus.COMPLETED,
        references=[],
    )

    # Assert
    mock_update_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_update_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "update_message_log", spec=True)
def test_update_message_log_entry__calls_chat_service__with_text_AI(
    mock_update_message_log: "Mock",
    logger: MessageStepLogger,
    sample_message_log: MessageLog,
) -> None:
    """
    Purpose: Verify update_message_log_entry passes text to chat service.
    Why this matters: Text content can be updated to reflect progress.
    Setup summary: Mock chat service, call update_message_log_entry with text, verify text parameter.
    """
    # Arrange
    # Act
    logger.update_message_log_entry(
        message_log=sample_message_log,
        text="Updated text",
        status=MessageLogStatus.COMPLETED,
        references=[],
    )

    # Assert
    mock_update_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_update_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["text"] == "Updated text"  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "update_message_log", spec=True)
def test_update_message_log_entry__calls_chat_service__with_custom_details_AI(
    mock_update_message_log: "Mock",
    logger: MessageStepLogger,
    sample_message_log: MessageLog,
) -> None:
    """
    Purpose: Verify update_message_log_entry passes custom details to chat service.
    Why this matters: Details can be updated with additional event information.
    Setup summary: Mock chat service, call update_message_log_entry with details, verify details parameter.
    """
    # Arrange
    custom_details = MessageLogDetails(
        data=[MessageLogEvent(type="WebSearch", text="Updated event")]
    )

    # Act
    logger.update_message_log_entry(
        message_log=sample_message_log,
        status=MessageLogStatus.COMPLETED,
        details=custom_details,
        references=[],
    )

    # Assert
    mock_update_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_update_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["details"] == custom_details  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "update_message_log", spec=True)
def test_update_message_log_entry__calls_chat_service__with_references_AI(
    mock_update_message_log: "Mock",
    logger: MessageStepLogger,
    sample_message_log: MessageLog,
) -> None:
    """
    Purpose: Verify update_message_log_entry passes references to chat service.
    Why this matters: References can be updated with new content links.
    Setup summary: Mock chat service, call update_message_log_entry with references, verify references parameter.
    """
    # Arrange
    references = [
        ContentReference(
            name="https://example.com/updated",
            sequence_number=0,
            source="web",
            url="https://example.com/updated",
            source_id="https://example.com/updated",
        )
    ]

    # Act
    logger.update_message_log_entry(
        message_log=sample_message_log,
        status=MessageLogStatus.COMPLETED,
        references=references,
    )

    # Assert
    mock_update_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_update_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(
        call_args.kwargs["uncited_references"], MessageLogUncitedReferences
    )  # type: ignore[attr-defined]
    assert len(call_args.kwargs["uncited_references"].data) == 1  # type: ignore[attr-defined]


@pytest.mark.ai
def test_update_message_log_entry__returns_none__when_message_log_id_not_set_AI(
    logger: MessageStepLogger,
) -> None:
    """
    Purpose: Verify update_message_log_entry returns None when message_log_id is not set.
    Why this matters: Operation should fail gracefully when log ID is missing.
    Setup summary: Create message log with no ID, call update, verify returns None.
    """
    # Arrange
    message_log_without_id = MessageLog(
        message_log_id=None,
        status=MessageLogStatus.RUNNING,
        order=1,
    )

    # Act
    result = logger.update_message_log_entry(
        message_log=message_log_without_id,
        status=MessageLogStatus.COMPLETED,
        references=[],
    )

    # Assert
    assert result is message_log_without_id


# Create or Update Message Log Tests
@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_or_update_message_log__creates_new__when_active_message_log_is_none_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_or_update_message_log creates new entry when no active log exists.
    Why this matters: New logs should be created when starting a new operation.
    Setup summary: Mock chat service, call with None active_message_log, verify create called.
    """
    # Arrange
    # Act
    logger.create_or_update_message_log(
        active_message_log=None,
        header="Web Search",
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "update_message_log", spec=True)
def test_create_or_update_message_log__updates_existing__when_active_message_log_provided_AI(
    mock_update_message_log: "Mock",
    logger: MessageStepLogger,
    sample_message_log: MessageLog,
) -> None:
    """
    Purpose: Verify create_or_update_message_log updates entry when active log exists.
    Why this matters: Existing logs should be updated to show progress.
    Setup summary: Mock chat service, call with active_message_log, verify update called.
    """
    # Arrange
    # Act
    logger.create_or_update_message_log(
        active_message_log=sample_message_log,
        header="Web Search",
    )

    # Assert
    mock_update_message_log.assert_called_once()  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_or_update_message_log__formats_text__with_header_only_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_or_update_message_log formats text correctly with header only.
    Why this matters: Header should be formatted in bold without extra content.
    Setup summary: Mock chat service, call with header only, verify text format.
    """
    # Arrange
    # Act
    logger.create_or_update_message_log(
        active_message_log=None,
        header="Internal Search",
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["text"] == "**Internal Search**"  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_or_update_message_log__formats_text__with_header_and_progress_message_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_or_update_message_log formats text with header and progress.
    Why this matters: Progress message should appear after header on new line.
    Setup summary: Mock chat service, call with header and progress, verify text format.
    """
    # Arrange
    # Act
    logger.create_or_update_message_log(
        active_message_log=None,
        header="Web Search",
        progress_message="Processing 5 sources...",
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["text"] == "**Web Search**\nProcessing 5 sources..."  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_or_update_message_log__uses_running_status__by_default_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_or_update_message_log uses RUNNING status by default.
    Why this matters: Default status should indicate operation is in progress.
    Setup summary: Mock chat service, call without status, verify RUNNING status.
    """
    # Arrange
    # Act
    logger.create_or_update_message_log(
        active_message_log=None,
        header="Web Search",
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["status"] == MessageLogStatus.RUNNING  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_or_update_message_log__uses_custom_status__when_provided_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_or_update_message_log uses custom status when provided.
    Why this matters: Status can be customized for different operation states.
    Setup summary: Mock chat service, call with COMPLETED status, verify status.
    """
    # Arrange
    # Act
    logger.create_or_update_message_log(
        active_message_log=None,
        header="Web Search",
        status=MessageLogStatus.COMPLETED,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_or_update_message_log__passes_details__when_provided_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_or_update_message_log passes details to underlying method.
    Why this matters: Details provide additional context about the operation.
    Setup summary: Mock chat service, call with details, verify details passed.
    """
    # Arrange
    custom_details = MessageLogDetails(
        data=[MessageLogEvent(type="WebSearch", text="Searching...")]
    )

    # Act
    logger.create_or_update_message_log(
        active_message_log=None,
        header="Web Search",
        details=custom_details,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["details"] == custom_details  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_or_update_message_log__passes_references__when_provided_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_or_update_message_log passes references to underlying method.
    Why this matters: References link the log to source content.
    Setup summary: Mock chat service, call with references, verify references passed.
    """
    # Arrange
    references = [
        ContentReference(
            name="https://example.com/page",
            sequence_number=0,
            source="web",
            url="https://example.com/page",
            source_id="https://example.com/page",
        )
    ]

    # Act
    logger.create_or_update_message_log(
        active_message_log=None,
        header="Web Search",
        references=references,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(
        call_args.kwargs["uncited_references"], MessageLogUncitedReferences
    )  # type: ignore[attr-defined]
    assert len(call_args.kwargs["uncited_references"].data) == 1  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "create_message_log", spec=True)
def test_create_or_update_message_log__uses_empty_references__when_none_provided_AI(
    mock_create_message_log: "Mock", logger: MessageStepLogger
) -> None:
    """
    Purpose: Verify create_or_update_message_log uses empty references when None provided.
    Why this matters: None references should be converted to empty list.
    Setup summary: Mock chat service, call with None references, verify empty list used.
    """
    # Arrange
    # Act
    logger.create_or_update_message_log(
        active_message_log=None,
        header="Web Search",
        references=None,
    )

    # Assert
    mock_create_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_create_message_log.call_args  # type: ignore[attr-defined]
    assert isinstance(
        call_args.kwargs["uncited_references"], MessageLogUncitedReferences
    )  # type: ignore[attr-defined]
    assert len(call_args.kwargs["uncited_references"].data) == 0  # type: ignore[attr-defined]


@pytest.mark.ai
@patch.object(ChatService, "update_message_log", spec=True)
def test_create_or_update_message_log__preserves_order__when_updating_AI(
    mock_update_message_log: "Mock",
    logger: MessageStepLogger,
    sample_message_log: MessageLog,
) -> None:
    """
    Purpose: Verify create_or_update_message_log preserves order when updating.
    Why this matters: Order must be preserved during updates.
    Setup summary: Mock chat service, call with active_message_log, verify order preserved.
    """
    # Arrange
    # Act
    logger.create_or_update_message_log(
        active_message_log=sample_message_log,
        header="Web Search",
        progress_message="Done",
        status=MessageLogStatus.COMPLETED,
    )

    # Assert
    mock_update_message_log.assert_called_once()  # type: ignore[attr-defined]
    call_args = mock_update_message_log.call_args  # type: ignore[attr-defined]
    assert call_args.kwargs["order"] == sample_message_log.order  # type: ignore[attr-defined]
