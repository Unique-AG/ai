"""
Tests for HistoryManager support of Responses API output items.

These tests verify that HistoryManager can store and handle ResponseOutputItem
objects alongside traditional LanguageModelMessage objects.
"""

import pytest
from openai.types.responses import (
    ResponseOutputText,
)

from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.language_model.schemas import (
    LanguageModelToolMessage,
)


class TestHistoryManagerResponsesAPI:
    """Test HistoryManager with Responses API output items."""

    def test_append_responses_output_to_history(self, history_manager_fixture):
        """Test that ResponseOutputItem objects can be appended to history."""
        # Arrange
        manager = history_manager_fixture
        output_items = [
            ResponseOutputText(
                type="output_text",
                text="Hello from Responses API",
                annotations=[],
            ),
            ResponseOutputText(
                type="output_text",
                text="Second output item",
                annotations=[],
            ),
        ]

        # Act
        manager.append_responses_output_to_history(output_items)

        # Assert
        assert len(manager._loop_history) == 2
        assert isinstance(manager._loop_history[0], ResponseOutputText)
        assert isinstance(manager._loop_history[1], ResponseOutputText)
        assert manager._loop_history[0].text == "Hello from Responses API"

    def test_append_multiple_output_items_to_history(self, history_manager_fixture):
        """Test that multiple ResponseOutputItem objects can be appended together."""
        # Arrange
        manager = history_manager_fixture
        output_items = [
            ResponseOutputText(type="output_text", text="First", annotations=[]),
            ResponseOutputText(type="output_text", text="Second", annotations=[]),
            ResponseOutputText(type="output_text", text="Third", annotations=[]),
        ]

        # Act
        manager.append_responses_output_to_history(output_items)

        # Assert
        assert len(manager._loop_history) == 3
        assert all(
            isinstance(item, ResponseOutputText) for item in manager._loop_history
        )
        assert manager._loop_history[0].text == "First"
        assert manager._loop_history[1].text == "Second"
        assert manager._loop_history[2].text == "Third"

    def test_mixed_history_completions_and_responses_api(self, history_manager_fixture):
        """Test that history can contain both Completions and Responses API items."""
        # Arrange
        manager = history_manager_fixture

        # Add Completions API message
        tool_message = LanguageModelToolMessage(
            content="Tool result",
            tool_call_id="tool_1",
            name="TestTool",
        )
        manager._loop_history.append(tool_message)

        # Add Responses API items
        responses_items = [
            ResponseOutputText(
                type="output_text",
                text="First response output",
                annotations=[],
            ),
            ResponseOutputText(
                type="output_text",
                text="Second response output",
                annotations=[],
            ),
        ]
        manager.append_responses_output_to_history(responses_items)

        # Assert
        assert len(manager._loop_history) == 3
        assert isinstance(manager._loop_history[0], LanguageModelToolMessage)
        assert isinstance(manager._loop_history[1], ResponseOutputText)
        assert isinstance(manager._loop_history[2], ResponseOutputText)

    def test_empty_output_list(self, history_manager_fixture):
        """Test that appending empty output list doesn't break anything."""
        # Arrange
        manager = history_manager_fixture
        initial_length = len(manager._loop_history)

        # Act
        manager.append_responses_output_to_history([])

        # Assert
        assert len(manager._loop_history) == initial_length

    def test_has_no_loop_messages_with_responses_api_items(
        self, history_manager_fixture
    ):
        """Test that has_no_loop_messages works with ResponseOutputItem."""
        # Arrange
        manager = history_manager_fixture

        # Initially empty
        assert manager.has_no_loop_messages() is True

        # Add Responses API item
        manager.append_responses_output_to_history(
            [
                ResponseOutputText(
                    type="output_text",
                    text="Test output",
                    annotations=[],
                )
            ]
        )

        # Should no longer be empty
        assert manager.has_no_loop_messages() is False


@pytest.fixture
def history_manager_fixture(mocker):
    """Create a HistoryManager instance for testing."""
    from logging import Logger

    from unique_toolkit.agentic.history_manager.history_manager import (
        HistoryManagerConfig,
    )
    from unique_toolkit.agentic.reference_manager.reference_manager import (
        ReferenceManager,
    )
    from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
    from unique_toolkit.language_model.infos import LanguageModelInfo

    # Mock dependencies
    logger = mocker.Mock(spec=Logger)
    event = mocker.MagicMock()  # Use MagicMock for nested attribute access
    event.payload.user_message.text = "Test message"
    event.payload.chat_id = "chat_123"
    event.payload.user_message.id = "msg_123"

    config = HistoryManagerConfig()
    language_model = LanguageModelInfo.from_name(DEFAULT_GPT_4o)
    reference_manager = mocker.Mock(spec=ReferenceManager)

    return HistoryManager(
        logger=logger,
        event=event,
        config=config,
        language_model=language_model,
        reference_manager=reference_manager,
    )
