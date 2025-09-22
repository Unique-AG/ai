from unittest.mock import AsyncMock

import pytest

from unique_toolkit.agentic.tools.tool_progress_reporter import (
    DUMMY_REFERENCE_PLACEHOLDER,
    ProgressState,
    ToolExecutionStatus,
    ToolProgressReporter,
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
