
import pytest

from unique_toolkit.agentic.tools.tool_progress_reporter import (
    DUMMY_REFERENCE_PLACEHOLDER,
    ProgressState,
    ToolExecutionStatus,
    ToolProgressReporter,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelFunction


class TestToolProgressReporter:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__stores_status__with_all_fields(
        self,
        tool_progress_reporter: ToolProgressReporter,
        tool_call: LanguageModelFunction,
    ) -> None:
        """
        Purpose: Verify notify_from_tool_call stores tool status with all provided fields.
        Why this matters: Tool status tracking is essential for progress reporting to users.
        Setup summary: Call notify with all fields populated, verify status is stored correctly.
        """
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

    @pytest.mark.ai
    def test_replace_placeholders__converts_placeholders__to_superscript_numbers(
        self, tool_progress_reporter: ToolProgressReporter
    ) -> None:
        """
        Purpose: Verify placeholder strings are replaced with superscript reference numbers.
        Why this matters: Reference placeholders must be converted to visible citations in output.
        Setup summary: Provide message with placeholders, verify numbered superscripts are inserted.
        """
        # Arrange
        message = (
            f"Test{DUMMY_REFERENCE_PLACEHOLDER}message{DUMMY_REFERENCE_PLACEHOLDER}"
        )

        # Act
        result = tool_progress_reporter._replace_placeholders(message, start_number=1)

        # Assert
        assert result == "Test<sup>1</sup>message<sup>2</sup>"

    @pytest.mark.ai
    def test_correct_reference_sequence__renumbers_references__starting_from_given_number(
        self, tool_progress_reporter: ToolProgressReporter
    ) -> None:
        """
        Purpose: Verify references are renumbered sequentially from the given start number.
        Why this matters: Ensures consistent reference numbering across multiple tool calls.
        Setup summary: Provide references with sequence 0, verify they are renumbered 1, 2.
        """
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

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_publish__calls_modify_assistant_message__with_tool_statuses(
        self,
        tool_progress_reporter: ToolProgressReporter,
        tool_call: LanguageModelFunction,
    ) -> None:
        """
        Purpose: Verify publish calls modify_assistant_message_async on the chat service.
        Why this matters: Publishing progress updates requires modifying the assistant message.
        Setup summary: Add a tool status, call publish, verify chat service method was called.
        """
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
