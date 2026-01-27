from unittest.mock import Mock

import pytest

from unique_toolkit.agentic.tools.tool_progress_reporter import (
    MessageLogToolProgressReporter,
    ProgressState,
)
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelFunction


@pytest.fixture
def message_log_reporter(
    message_step_logger: Mock,
) -> MessageLogToolProgressReporter:
    """Create a MessageLogToolProgressReporter instance."""
    return MessageLogToolProgressReporter(message_step_logger)


class TestMessageLogToolProgressReporter:
    """Tests for MessageLogToolProgressReporter."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__creates_new_message_log__on_first_call(
        self,
        message_log_reporter: MessageLogToolProgressReporter,
        tool_call: LanguageModelFunction,
    ) -> None:
        """
        Purpose: Verify that first call creates a new message log entry.
        Why this matters: New tool calls should create fresh message log entries.
        Setup summary: Call notify_from_tool_call, verify create_or_update_message_log called with None.
        """
        # Act
        await message_log_reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Processing",
            state=ProgressState.RUNNING,
        )

        # Assert
        call_kwargs = message_log_reporter._message_step_logger.create_or_update_message_log.call_args.kwargs
        assert call_kwargs["active_message_log"] is None
        assert call_kwargs["header"] == "Test Tool"
        # Message is wrapped in underscores for markdown italic formatting
        assert call_kwargs["progress_message"] == "_Processing_"
        assert call_kwargs["status"] == MessageLogStatus.RUNNING
        assert call_kwargs["references"] is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__updates_existing_log__on_subsequent_call(
        self,
        message_log_reporter: MessageLogToolProgressReporter,
        message_step_logger: Mock,
        tool_call: LanguageModelFunction,
    ) -> None:
        """
        Purpose: Verify that subsequent calls update the existing message log.
        Why this matters: Updates to same tool call should modify existing entry, not create new.
        Setup summary: Call twice with same tool_call, verify second call passes existing log.
        """
        # Arrange
        first_log = MessageLog(
            message_log_id="log_1", order=1, status=MessageLogStatus.RUNNING
        )
        message_step_logger.create_or_update_message_log.return_value = first_log

        # Act - First call
        await message_log_reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Starting",
            state=ProgressState.STARTED,
        )

        # Act - Second call
        await message_log_reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Completed",
            state=ProgressState.FINISHED,
        )

        # Assert - Second call should pass the existing log
        calls = message_step_logger.create_or_update_message_log.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["active_message_log"] is None
        assert calls[1].kwargs["active_message_log"] == first_log

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__forwards_references__when_provided(
        self,
        message_log_reporter: MessageLogToolProgressReporter,
        tool_call: LanguageModelFunction,
    ) -> None:
        """
        Purpose: Verify that references are forwarded to the message step logger.
        Why this matters: References should be passed through for display in the UI.
        Setup summary: Call with references, verify they are passed to create_or_update_message_log.
        """
        # Arrange
        references = [
            ContentReference(
                sequence_number=1,
                id="ref_1",
                message_id="msg_1",
                name="Reference 1",
                source="source",
                source_id="src_1",
                url="http://example.com",
            )
        ]

        # Act
        await message_log_reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Found results",
            state=ProgressState.FINISHED,
            references=references,
        )

        # Assert
        call_kwargs = message_log_reporter._message_step_logger.create_or_update_message_log.call_args.kwargs
        assert call_kwargs["references"] == references

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__tracks_multiple_tool_calls__independently(
        self,
        message_log_reporter: MessageLogToolProgressReporter,
        message_step_logger: Mock,
    ) -> None:
        """
        Purpose: Verify that different tool calls are tracked independently.
        Why this matters: Parallel tool calls should each have their own message log.
        Setup summary: Call with different tool_call ids, verify separate logs are tracked.
        """
        # Arrange
        tool_call_1 = LanguageModelFunction(id="tool_1", name="search")
        tool_call_2 = LanguageModelFunction(id="tool_2", name="analyze")
        log_1 = MessageLog(
            message_log_id="log_1", order=1, status=MessageLogStatus.RUNNING
        )
        log_2 = MessageLog(
            message_log_id="log_2", order=2, status=MessageLogStatus.RUNNING
        )
        message_step_logger.create_or_update_message_log.side_effect = [log_1, log_2]

        # Act
        await message_log_reporter.notify_from_tool_call(
            tool_call=tool_call_1,
            name="Search",
            message="Searching",
            state=ProgressState.RUNNING,
        )
        await message_log_reporter.notify_from_tool_call(
            tool_call=tool_call_2,
            name="Analyze",
            message="Analyzing",
            state=ProgressState.RUNNING,
        )

        # Assert
        assert message_log_reporter._active_message_logs["tool_1"] == log_1
        assert message_log_reporter._active_message_logs["tool_2"] == log_2
