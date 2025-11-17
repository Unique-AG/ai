from unittest.mock import AsyncMock

import pytest

from unique_toolkit.agentic.tools.tool_progress_reporter import (
    DUMMY_REFERENCE_PLACEHOLDER,
    ProgressState,
    ToolExecutionStatus,
    ToolProgressReporter,
    ToolProgressReporterConfig,
    ToolWithToolProgressReporter,
    track_tool_progress,
)
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
                description="Test reference description",
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
                description="Test reference 1 description",
            ),
            ContentReference(
                sequence_number=0,
                id="2",
                message_id="2",
                name="2",
                source="2",
                source_id="2",
                url="2",
                description="Test reference 2 description",
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
                    description="Test reference description",
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
                        description="Test reference description",
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
