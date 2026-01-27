import pytest

from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
    ToolWithToolProgressReporter,
    track_tool_progress,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelFunction


class TestToolProgressDecorator:
    class DummyTool(ToolWithToolProgressReporter):
        def __init__(self, tool_progress_reporter: ToolProgressReporter) -> None:
            self.tool_progress_reporter = tool_progress_reporter

        @track_tool_progress(
            message="Processing",
            on_start_state=ProgressState.STARTED,
            on_success_state=ProgressState.FINISHED,
            on_success_message="Completed",
            requires_new_assistant_message=True,
        )
        async def execute(
            self, tool_call: LanguageModelFunction, notification_tool_name: str
        ) -> dict:
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

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_track_tool_progress__updates_status_to_finished__on_success(
        self,
        tool_progress_reporter: ToolProgressReporter,
        tool_call: LanguageModelFunction,
    ) -> None:
        """
        Purpose: Verify decorator updates status to FINISHED with success message on successful execution.
        Why this matters: Users need to see completion status after tool execution succeeds.
        Setup summary: Execute decorated method successfully, verify final status is FINISHED.
        """
        # Arrange
        tool = self.DummyTool(tool_progress_reporter)

        # Act
        await tool.execute(tool_call, "Test Tool")

        # Assert
        assert len(tool_progress_reporter.tool_statuses) == 1
        status = tool_progress_reporter.tool_statuses[tool_call.id]
        assert status.state == ProgressState.FINISHED
        assert status.message == "Completed"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_track_tool_progress__updates_status_to_failed__on_exception(
        self,
        tool_progress_reporter: ToolProgressReporter,
        tool_call: LanguageModelFunction,
    ) -> None:
        """
        Purpose: Verify decorator updates status to FAILED when execution raises an exception.
        Why this matters: Users need to see failure status when tool execution fails.
        Setup summary: Execute decorated method that raises, verify status is FAILED.
        """

        # Arrange
        class ErrorTool(ToolWithToolProgressReporter):
            def __init__(self, tool_progress_reporter: ToolProgressReporter) -> None:
                self.tool_progress_reporter = tool_progress_reporter

            @track_tool_progress(message="Processing")
            async def execute(
                self, tool_call: LanguageModelFunction, notification_tool_name: str
            ) -> None:
                raise ValueError("Test error")

        tool = ErrorTool(tool_progress_reporter)

        # Act & Assert
        with pytest.raises(ValueError):
            await tool.execute(tool_call, "Test Tool")

        status = tool_progress_reporter.tool_statuses[tool_call.id]
        assert status.state == ProgressState.FAILED
