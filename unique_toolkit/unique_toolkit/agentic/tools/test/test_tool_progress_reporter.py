from unittest.mock import AsyncMock, Mock

import pytest

from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    DUMMY_REFERENCE_PLACEHOLDER,
    CompositeToolProgressReporter,
    MessageLogToolProgressReporter,
    ProgressState,
    ToolExecutionStatus,
    ToolProgressReporter,
    ToolProgressReporterConfig,
    ToolProgressReporterProtocol,
    ToolWithToolProgressReporter,
    track_tool_progress,
)
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelFunction


@pytest.fixture
def chat_service():
    return AsyncMock(spec=ChatService)


@pytest.fixture
def tool_progress_reporter(chat_service):
    return ToolProgressReporter(chat_service)


@pytest.fixture
def tool_call():
    return LanguageModelFunction(id="test_id", name="test_tool")


class TestToolProgressReporter:
    @pytest.mark.asyncio
    async def test_notify_from_tool_call(self, tool_progress_reporter, tool_call):
        # Arrange
        name = "Test Tool"
        message = "Processing..."
        state = ProgressState.RUNNING
        references = [
            ContentReference(
                sequence_number=1,
                id="1",
                message_id="1",
                name="1",
                source="1",
                source_id="1",
                url="1",
            )
        ]

        # Act
        await tool_progress_reporter.notify_from_tool_call(
            tool_call=tool_call,
            name=name,
            message=message,
            state=state,
            references=references,
            requires_new_assistant_message=True,
        )

        # Assert
        assert tool_call.id in tool_progress_reporter.tool_statuses
        status = tool_progress_reporter.tool_statuses[tool_call.id]
        assert status.name == name
        assert status.message == message
        assert status.state == state
        assert status.references == references
        assert tool_progress_reporter.requires_new_assistant_message is True

    def test_replace_placeholders(self, tool_progress_reporter):
        # Arrange
        message = (
            f"Test{DUMMY_REFERENCE_PLACEHOLDER}message{DUMMY_REFERENCE_PLACEHOLDER}"
        )

        # Act
        result = tool_progress_reporter._replace_placeholders(message, start_number=1)

        # Assert
        assert result == "Test<sup>1</sup>message<sup>2</sup>"

    def test_correct_reference_sequence(self, tool_progress_reporter):
        # Arrange
        references = [
            ContentReference(
                sequence_number=0,
                id="1",
                message_id="1",
                name="1",
                source="1",
                source_id="1",
                url="1",
            ),
            ContentReference(
                sequence_number=0,
                id="2",
                message_id="2",
                name="2",
                source="2",
                source_id="2",
                url="2",
            ),
        ]

        # Act
        result = tool_progress_reporter._correct_reference_sequence(
            references, start_number=1
        )

        # Assert
        assert len(result) == 2
        assert result[0].sequence_number == 1
        assert result[1].sequence_number == 2

    @pytest.mark.asyncio
    async def test_publish_updates_chat_service(
        self, tool_progress_reporter, tool_call
    ):
        # Arrange
        status = ToolExecutionStatus(
            name="Test Tool",
            message="Test message",
            state=ProgressState.FINISHED,
            references=[
                ContentReference(
                    sequence_number=1,
                    id="1",
                    message_id="1",
                    name="1",
                    source="1",
                    source_id="1",
                    url="1",
                )
            ],
        )
        tool_progress_reporter.tool_statuses[tool_call.id] = status

        # Act
        await tool_progress_reporter.publish()

        # Assert
        tool_progress_reporter.chat_service.modify_assistant_message_async.assert_called_once()


class TestToolProgressDecorator:
    class DummyTool(ToolWithToolProgressReporter):
        def __init__(self, tool_progress_reporter):
            self.tool_progress_reporter = tool_progress_reporter

        @track_tool_progress(
            message="Processing",
            on_start_state=ProgressState.STARTED,
            on_success_state=ProgressState.FINISHED,
            on_success_message="Completed",
            requires_new_assistant_message=True,
        )
        async def execute(self, tool_call, notification_tool_name):
            return {
                "references": [
                    ContentReference(
                        sequence_number=1,
                        id="1",
                        message_id="1",
                        name="1",
                        source="1",
                        source_id="1",
                        url="1",
                    )
                ]
            }

    @pytest.mark.asyncio
    async def test_decorator_success_flow(self, tool_progress_reporter, tool_call):
        # Arrange
        tool = self.DummyTool(tool_progress_reporter)

        # Act
        await tool.execute(tool_call, "Test Tool")

        # Assert
        assert len(tool_progress_reporter.tool_statuses) == 1
        status = tool_progress_reporter.tool_statuses[tool_call.id]
        assert status.state == ProgressState.FINISHED
        assert status.message == "Completed"

    @pytest.mark.asyncio
    async def test_decorator_error_flow(self, tool_progress_reporter, tool_call):
        # Arrange
        class ErrorTool(ToolWithToolProgressReporter):
            def __init__(self, tool_progress_reporter):
                self.tool_progress_reporter = tool_progress_reporter

            @track_tool_progress(message="Processing")
            async def execute(self, tool_call, notification_tool_name):
                raise ValueError("Test error")

        tool = ErrorTool(tool_progress_reporter)

        # Act & Assert
        with pytest.raises(ValueError):
            await tool.execute(tool_call, "Test Tool")

        status = tool_progress_reporter.tool_statuses[tool_call.id]
        assert status.state == ProgressState.FAILED


class TestToolProgressReporterConfig:
    """Tests for ToolProgressReporterConfig and custom display configuration."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_config__uses_default_templates__when_no_config_provided(
        self, chat_service, tool_call
    ) -> None:
        """
        Purpose: Verify that default state-to-display templates are used when no config is provided.
        Why this matters: Ensures backward compatibility and default behavior.
        Setup summary: Create reporter without config, add status, verify default template is used.
        """
        # Arrange
        reporter = ToolProgressReporter(chat_service)

        # Act
        await reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Processing data",
            state=ProgressState.RUNNING,
        )

        # Assert
        assert tool_call.id in reporter.tool_statuses
        chat_service.modify_assistant_message_async.assert_called()
        call_args = chat_service.modify_assistant_message_async.call_args
        content = call_args.kwargs["content"]
        assert "Test Tool" in content
        assert "🟡" in content  # Default emoji for RUNNING state
        assert "Processing data" in content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_config__uses_custom_templates__when_config_provided(
        self, chat_service, tool_call
    ) -> None:
        """
        Purpose: Verify that custom templates are used when provided via config.
        Why this matters: Enables customization of progress display format.
        Setup summary: Create reporter with custom template, verify custom format is used.
        """
        # Arrange
        custom_config = ToolProgressReporterConfig(
            state_to_display_template={
                "started": "⚪ {tool_name}: {message}",
                "running": "⏳ {tool_name}: {message}",
                "finished": "✅ {tool_name}: {message}",
                "failed": "❌ {tool_name}: {message}",
            }
        )
        reporter = ToolProgressReporter(chat_service, config=custom_config)

        # Act
        await reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="My Tool",
            message="Working on it",
            state=ProgressState.RUNNING,
        )

        # Assert
        chat_service.modify_assistant_message_async.assert_called()
        call_args = chat_service.modify_assistant_message_async.call_args
        content = call_args.kwargs["content"]
        assert "⏳ My Tool: Working on it" in content
        assert "🟡" not in content  # Default emoji should not appear

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_config__skips_states_with_empty_template__when_state_hidden(
        self, chat_service, tool_call
    ) -> None:
        """
        Purpose: Verify that states with empty string templates are not displayed.
        Why this matters: Allows selective display of only certain states (e.g., hide STARTED).
        Setup summary: Create config with empty string for RUNNING state, verify message is not displayed.
        """
        # Arrange
        custom_config = ToolProgressReporterConfig(
            state_to_display_template={
                "started": "",
                "running": "",  # Empty string hides RUNNING state
                "finished": "✅ {tool_name}: {message}",
                "failed": "❌ {tool_name}: {message}",
            }
        )
        reporter = ToolProgressReporter(chat_service, config=custom_config)

        # Act
        await reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Processing",
            state=ProgressState.RUNNING,
        )

        # Assert
        chat_service.modify_assistant_message_async.assert_called()
        call_args = chat_service.modify_assistant_message_async.call_args
        content = call_args.kwargs["content"]
        # Content should not contain the message since RUNNING template is empty
        assert "Processing" not in content
        assert "Test Tool" not in content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_config__formats_placeholders_correctly__with_multiple_tools(
        self, chat_service
    ) -> None:
        """
        Purpose: Verify that {tool_name} and {message} placeholders are replaced correctly for multiple tools.
        Why this matters: Ensures template formatting works correctly in multi-tool scenarios.
        Setup summary: Add multiple tool statuses with different names/messages, verify formatting.
        """
        # Arrange
        custom_config = ToolProgressReporterConfig(
            state_to_display_template={
                "started": "○ {tool_name} - {message}",
                "running": "▶️ {tool_name} - {message}",
                "finished": "✓ {tool_name} - {message}",
                "failed": "✗ {tool_name} - {message}",
            }
        )
        reporter = ToolProgressReporter(chat_service, config=custom_config)
        tool_call_1 = LanguageModelFunction(id="tool_1", name="search")
        tool_call_2 = LanguageModelFunction(id="tool_2", name="analyze")

        # Act
        await reporter.notify_from_tool_call(
            tool_call=tool_call_1,
            name="Search Tool",
            message="Searching database",
            state=ProgressState.RUNNING,
        )
        await reporter.notify_from_tool_call(
            tool_call=tool_call_2,
            name="Analysis Tool",
            message="Analyzing results",
            state=ProgressState.FINISHED,
        )

        # Assert
        call_args = chat_service.modify_assistant_message_async.call_args
        content = call_args.kwargs["content"]
        assert "▶️ Search Tool - Searching database" in content
        assert "✓ Analysis Tool - Analyzing results" in content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_config__shows_only_finished_state__when_only_finished_configured(
        self, chat_service, tool_call
    ) -> None:
        """
        Purpose: Verify selective state display shows only FINISHED when other states use empty templates.
        Why this matters: Use case where user only wants final results, not intermediate steps.
        Setup summary: Configure only FINISHED with content, send STARTED and FINISHED, verify only FINISHED appears.
        """
        # Arrange
        custom_config = ToolProgressReporterConfig(
            state_to_display_template={
                "started": "",  # Empty template hides STARTED
                "running": "",  # Empty template hides RUNNING
                "finished": "Done: {tool_name} - {message}",
                "failed": "Failed: {tool_name} - {message}",
            }
        )
        reporter = ToolProgressReporter(chat_service, config=custom_config)

        # Act - Send STARTED state (should not appear)
        await reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Starting",
            state=ProgressState.STARTED,
        )

        # Get first call content
        first_call_args = chat_service.modify_assistant_message_async.call_args
        first_content = first_call_args.kwargs["content"]

        # Act - Update to FINISHED state (should appear)
        await reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Completed successfully",
            state=ProgressState.FINISHED,
        )

        # Assert
        final_call_args = chat_service.modify_assistant_message_async.call_args
        final_content = final_call_args.kwargs["content"]

        # STARTED state should not appear in first call
        assert "Starting" not in first_content

        # FINISHED state should appear in final call
        assert "Done: Test Tool - Completed successfully" in final_content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_config__handles_all_empty_templates__when_all_states_hidden(
        self, chat_service, tool_call
    ) -> None:
        """
        Purpose: Verify that all empty string templates result in no messages being displayed.
        Why this matters: Edge case handling and allows disabling all progress display.
        Setup summary: Create config with all empty templates, verify no tool messages appear.
        """
        # Arrange
        custom_config = ToolProgressReporterConfig(
            state_to_display_template={
                "started": "",
                "running": "",
                "finished": "",
                "failed": "",
            }
        )
        reporter = ToolProgressReporter(chat_service, config=custom_config)

        # Act
        await reporter.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Processing",
            state=ProgressState.RUNNING,
        )

        # Assert
        chat_service.modify_assistant_message_async.assert_called()
        call_args = chat_service.modify_assistant_message_async.call_args
        content = call_args.kwargs["content"]

        # Should only have the progress start text and newlines, no actual messages
        assert "Test Tool" not in content
        assert "Processing" not in content


class TestMessageLogToolProgressReporter:
    """Tests for MessageLogToolProgressReporter."""

    @pytest.fixture
    def message_step_logger(self) -> Mock:
        """Create a mock MessageStepLogger."""
        logger = Mock(spec=MessageStepLogger)
        logger.create_or_update_message_log = Mock(
            return_value=MessageLog(
                message_log_id="log_1", order=1, status=MessageLogStatus.RUNNING
            )
        )
        return logger

    @pytest.fixture
    def message_log_reporter(
        self, message_step_logger: Mock
    ) -> MessageLogToolProgressReporter:
        """Create a MessageLogToolProgressReporter instance."""
        return MessageLogToolProgressReporter(message_step_logger)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__creates_message_log__on_first_call(
        self, message_log_reporter: MessageLogToolProgressReporter, tool_call
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
        call_kwargs = (
            message_log_reporter._message_step_logger.create_or_update_message_log.call_args.kwargs
        )
        assert call_kwargs["active_message_log"] is None
        assert call_kwargs["header"] == "Test Tool"
        assert call_kwargs["progress_message"] == "Processing"
        assert call_kwargs["status"] == MessageLogStatus.RUNNING
        assert call_kwargs["references"] is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__updates_existing_log__on_subsequent_call(
        self,
        message_log_reporter: MessageLogToolProgressReporter,
        message_step_logger: Mock,
        tool_call,
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
        self, message_log_reporter: MessageLogToolProgressReporter, tool_call
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
        call_kwargs = (
            message_log_reporter._message_step_logger.create_or_update_message_log.call_args.kwargs
        )
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


class TestCompositeToolProgressReporter:
    """Tests for CompositeToolProgressReporter."""

    @pytest.fixture
    def mock_reporter_1(self) -> Mock:
        """Create first mock reporter."""
        reporter = Mock(spec=ToolProgressReporterProtocol)
        reporter.notify_from_tool_call = AsyncMock()
        return reporter

    @pytest.fixture
    def mock_reporter_2(self) -> Mock:
        """Create second mock reporter."""
        reporter = Mock(spec=ToolProgressReporterProtocol)
        reporter.notify_from_tool_call = AsyncMock()
        return reporter

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__calls_all_reporters__with_same_args(
        self, mock_reporter_1: Mock, mock_reporter_2: Mock, tool_call
    ) -> None:
        """
        Purpose: Verify that composite broadcasts to all reporters with identical arguments.
        Why this matters: All reporters should receive the same notification data.
        Setup summary: Create composite with two reporters, call notify, verify both called.
        """
        # Arrange
        composite = CompositeToolProgressReporter([mock_reporter_1, mock_reporter_2])
        references = [
            ContentReference(
                sequence_number=1,
                id="ref_1",
                message_id="msg_1",
                name="Ref",
                source="src",
                source_id="src_1",
                url="http://example.com",
            )
        ]

        # Act
        await composite.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Processing",
            state=ProgressState.RUNNING,
            references=references,
        )

        # Assert
        for reporter in [mock_reporter_1, mock_reporter_2]:
            reporter.notify_from_tool_call.assert_called_once_with(
                tool_call=tool_call,
                name="Test Tool",
                message="Processing",
                state=ProgressState.RUNNING,
                references=references,
            )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__handles_empty_list__without_error(
        self, tool_call
    ) -> None:
        """
        Purpose: Verify that composite handles empty reporter list gracefully.
        Why this matters: Edge case where no reporters are configured should not crash.
        Setup summary: Create composite with empty list, call notify, verify no error.
        """
        # Arrange
        composite = CompositeToolProgressReporter([])

        # Act & Assert - Should not raise
        await composite.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Processing",
            state=ProgressState.RUNNING,
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__calls_single_reporter__when_one_provided(
        self, mock_reporter_1: Mock, tool_call
    ) -> None:
        """
        Purpose: Verify that composite works correctly with a single reporter.
        Why this matters: Common case where only one reporter type is needed.
        Setup summary: Create composite with one reporter, verify it's called.
        """
        # Arrange
        composite = CompositeToolProgressReporter([mock_reporter_1])

        # Act
        await composite.notify_from_tool_call(
            tool_call=tool_call,
            name="Test Tool",
            message="Done",
            state=ProgressState.FINISHED,
        )

        # Assert
        mock_reporter_1.notify_from_tool_call.assert_called_once()
