from unittest.mock import Mock

import pytest

from unique_toolkit.agentic.tools.tool_progress_reporter import (
    CompositeToolProgressReporter,
    ProgressState,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelFunction


class TestCompositeToolProgressReporter:
    """Tests for CompositeToolProgressReporter."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notify_from_tool_call__calls_all_reporters__with_same_args(
        self,
        mock_reporter_1: Mock,
        mock_reporter_2: Mock,
        tool_call: LanguageModelFunction,
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
        self, tool_call: LanguageModelFunction
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
        self, mock_reporter_1: Mock, tool_call: LanguageModelFunction
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
