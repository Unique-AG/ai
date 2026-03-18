"""
Tests for LoopTokenReducer support of Responses API output items.

These tests verify that LoopTokenReducer can handle mixed history containing
both LanguageModelMessage and ResponseOutputItem objects, including token
counting and reduction logic.
"""

import pytest
from openai.types.responses import (
    ResponseOutputText,
)

from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)


class TestLoopTokenReducerResponsesAPI:
    """Test LoopTokenReducer with Responses API output items."""

    def test_construct_history_with_response_output_items(
        self, loop_token_reducer_fixture
    ):
        """Test that _construct_history handles ResponseOutputItem objects."""
        # Arrange
        reducer = loop_token_reducer_fixture
        db_history = [LanguageModelUserMessage(content="Hello")]
        loop_history = [
            ResponseOutputText(
                type="output_text",
                text="Let me analyze this...",
                annotations=[],
            ),
            ResponseOutputText(
                type="output_text",
                text="x = 42",
                annotations=[],
            ),
        ]

        # Act
        messages = reducer._construct_history(db_history, loop_history)

        # Assert
        assert isinstance(messages, LanguageModelMessages)
        assert len(messages.root) == 3  # 1 from DB + 2 from loop

    def test_count_message_tokens_with_response_output_items(
        self, loop_token_reducer_fixture
    ):
        """Test token counting for messages containing ResponseOutputItem."""
        # Arrange
        reducer = loop_token_reducer_fixture
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="Hello"),
                ResponseOutputText(
                    type="output_text",
                    text="This is a test reasoning trace",
                    annotations=[],
                ),
                LanguageModelToolMessage(
                    content="Tool result",
                    tool_call_id="tool_1",
                    name="TestTool",
                ),
            ]
        )

        # Act
        token_count = reducer._count_message_tokens(messages)

        # Assert
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_count_message_tokens_pure_language_model_messages(
        self, loop_token_reducer_fixture
    ):
        """Test that pure LanguageModelMessage counting uses fast path."""
        # Arrange
        reducer = loop_token_reducer_fixture
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="Hello world"),
                LanguageModelToolMessage(
                    content="Result",
                    tool_call_id="tool_1",
                    name="TestTool",
                ),
            ]
        )

        # Act
        token_count = reducer._count_message_tokens(messages)

        # Assert
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_should_reduce_message_skips_response_output_items(
        self, loop_token_reducer_fixture
    ):
        """Test that ResponseOutputItem instances are not reduced."""
        # Arrange
        reducer = loop_token_reducer_fixture

        output_text_item = ResponseOutputText(
            type="output_text",
            text="Test output",
            annotations=[],
        )
        another_output_item = ResponseOutputText(
            type="output_text",
            text="Another output",
            annotations=[],
        )
        tool_message = LanguageModelToolMessage(
            content="Result",
            tool_call_id="tool_1",
            name="TestTool",
        )

        # Act & Assert
        assert reducer._should_reduce_message(output_text_item) is False
        assert reducer._should_reduce_message(another_output_item) is False
        assert reducer._should_reduce_message(tool_message) is True

    def test_reduce_message_length_preserves_response_output_items(
        self, loop_token_reducer_fixture, mocker
    ):
        """Test that reduction preserves ResponseOutputItem instances."""
        # Arrange
        reducer = loop_token_reducer_fixture

        # Mock the reference manager to avoid actual chunk operations
        mocker.patch.object(
            reducer._reference_manager,
            "get_chunks_of_tool",
            return_value=[],
        )
        mocker.patch.object(
            reducer._reference_manager,
            "replace",
            return_value=None,
        )

        history = [
            ResponseOutputText(
                type="output_text",
                text="Analyzing...",
                annotations=[],
            ),
            LanguageModelToolMessage(
                content="Tool result",
                tool_call_id="tool_1",
                name="TestTool",
            ),
            ResponseOutputText(
                type="output_text",
                text="x = 1",
                annotations=[],
            ),
        ]

        # Act
        reduced_history = (
            reducer._reduce_message_length_by_reducing_sources_in_tool_response(
                history, overshoot_factor=2.0
            )
        )

        # Assert
        assert len(reduced_history) == 3
        assert isinstance(reduced_history[0], ResponseOutputText)
        assert isinstance(reduced_history[1], LanguageModelToolMessage)
        assert isinstance(reduced_history[2], ResponseOutputText)

    def test_mixed_history_token_counting_accuracy(self, loop_token_reducer_fixture):
        """Test that mixed history token counting is reasonably accurate."""
        # Arrange
        reducer = loop_token_reducer_fixture

        # Create messages with known approximate token counts
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="Hello world"),  # ~2-3 tokens
                ResponseOutputText(
                    type="output_text",
                    text="This is a reasoning trace",  # ~5-6 tokens
                    annotations=[],
                ),
            ]
        )

        # Act
        token_count = reducer._count_message_tokens(messages)

        # Assert
        # Should be roughly 7-15 tokens (accounting for JSON overhead)
        assert 5 < token_count < 50  # Reasonable bounds


@pytest.fixture
def loop_token_reducer_fixture(mocker):
    """Create a LoopTokenReducer instance for testing."""
    from logging import Logger

    from unique_toolkit.agentic.history_manager.loop_token_reducer import (
        LoopTokenReducer,
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

    language_model = LanguageModelInfo.from_name(DEFAULT_GPT_4o)
    reference_manager = mocker.Mock(spec=ReferenceManager)

    # Mock reference manager methods
    reference_manager.get_chunks_of_all_tools.return_value = []
    reference_manager.get_chunks.return_value = []

    return LoopTokenReducer(
        logger=logger,
        event=event,
        max_history_tokens=1000,
        has_uploaded_content_config=False,
        language_model=language_model,
        reference_manager=reference_manager,
    )
