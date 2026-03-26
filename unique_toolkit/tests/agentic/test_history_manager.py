import json
from logging import Logger
from unittest.mock import MagicMock

import pytest

from unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
    HistoryManagerConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.content.schemas import ContentChunk


@pytest.mark.ai
def test_get_tool_call_result_for_loop_history__includes_pdf_content_id_when_enabled() -> (
    None
):
    """
    Purpose: Verify loop-history serialization preserves PDF content_id values.
    Why this matters: OpenPdf depends on the model seeing valid content IDs.
    Setup summary: Create HistoryManager with feature enabled and serialize a PDF chunk.
    """
    # Arrange
    history_manager = HistoryManager.__new__(HistoryManager)
    history_manager._logger = MagicMock(spec=Logger)
    history_manager._config = HistoryManagerConfig()
    history_manager._source_enumerator = 0

    tool_response = ToolCallResponse(
        id="tool-call-1",
        name="InternalSearch",
        content_chunks=[
            ContentChunk(
                id="cont_pdf_123",
                text="Relevant PDF excerpt",
                key="kb-report.pdf",
            )
        ],
    )

    # Act
    tool_message = history_manager._get_tool_call_result_for_loop_history(tool_response)

    # Assert
    assert json.loads(tool_message.content) == [
        {
            "source_number": 0,
            "content_id": "cont_pdf_123",
            "content": "Relevant PDF excerpt",
        }
    ]
    assert history_manager._source_enumerator == 1
