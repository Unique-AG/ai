"""
Tests for QwenForcedToolCallMiddleware and helper functions.

This file contains tests for the QwenForcedToolCallMiddleware class which
modifies messages for Qwen models to force tool calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai.types.chat import ChatCompletionNamedToolChoiceParam

from unique_toolkit.agentic.loop_runner.middleware.qwen_forced_tool_call import (
    QwenForcedToolCallMiddleware,
)
from unique_toolkit.agentic.loop_runner.middleware.qwen_forced_tool_call.helpers import (
    append_qwen_forced_tool_call_instruction,
    is_qwen_model,
)
from unique_toolkit.agentic.loop_runner.middleware.qwen_forced_tool_call.qwen_forced_tool_call import (
    QWEN_FORCED_TOOL_CALL_PROMPT_INSTRUCTION,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


# Fixtures
@pytest.fixture
def mock_inner_runner() -> AsyncMock:
    """Provide a mock inner loop runner."""
    runner = AsyncMock()
    runner.return_value = create_stream_response()
    return runner


@pytest.fixture
def mock_language_model() -> LanguageModelInfo:
    """Provide a language model info for tests."""
    return LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0513)


@pytest.fixture
def mock_qwen_model() -> LanguageModelInfo:
    """Provide a Qwen language model info for tests."""
    return LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)


@pytest.fixture
def mock_streaming_handler() -> MagicMock:
    """Provide a mock streaming handler."""
    handler = MagicMock()
    handler.complete_with_references_async = AsyncMock()
    return handler


@pytest.fixture
def sample_messages() -> LanguageModelMessages:
    """Provide sample messages for tests."""
    return LanguageModelMessages(
        root=[
            LanguageModelSystemMessage(content="You are a helpful assistant."),
            LanguageModelUserMessage(content="Search for documents"),
        ]
    )


@pytest.fixture
def sample_tool_choices() -> list[ChatCompletionNamedToolChoiceParam]:
    """Provide sample tool choices for tests."""
    return [{"type": "function", "function": {"name": "SearchTool"}}]


def create_stream_response(
    text: str = "Response text",
    references: list[ContentReference] | None = None,
) -> LanguageModelStreamResponse:
    """Helper function to create LanguageModelStreamResponse instances for testing."""
    return LanguageModelStreamResponse(
        message=LanguageModelStreamResponseMessage(
            id="msg_123",
            previous_message_id="prev_msg_123",
            role=LanguageModelMessageRole.ASSISTANT,
            text=text,
            original_text=text,
            references=references or [],
        ),
        tool_calls=None,
    )


# Helper Function Tests - is_qwen_model
class TestIsQwenModel:
    @pytest.mark.ai
    def test_is_qwen_model__returns_true__for_qwen_language_model_info(
        self, mock_qwen_model: LanguageModelInfo
    ) -> None:
        """
        Purpose: Verify is_qwen_model returns True for Qwen LanguageModelInfo.
        Why this matters: Qwen models need special handling for tool calls.
        """
        # Act
        result = is_qwen_model(model=mock_qwen_model)

        # Assert
        assert result is True

    @pytest.mark.ai
    def test_is_qwen_model__returns_false__for_non_qwen_language_model_info(
        self, mock_language_model: LanguageModelInfo
    ) -> None:
        """
        Purpose: Verify is_qwen_model returns False for non-Qwen LanguageModelInfo.
        Why this matters: Non-Qwen models should not receive special handling.
        """
        # Act
        result = is_qwen_model(model=mock_language_model)

        # Assert
        assert result is False

    @pytest.mark.ai
    def test_is_qwen_model__returns_true__for_qwen_string(self) -> None:
        """
        Purpose: Verify is_qwen_model returns True for string containing 'qwen'.
        Why this matters: Model names can be passed as strings.
        """
        # Act & Assert
        assert is_qwen_model(model="qwen-3") is True
        assert is_qwen_model(model="QWEN-72B") is True
        assert is_qwen_model(model="litellm/qwen-model") is True

    @pytest.mark.ai
    def test_is_qwen_model__returns_false__for_non_qwen_string(self) -> None:
        """
        Purpose: Verify is_qwen_model returns False for string not containing 'qwen'.
        Why this matters: Non-Qwen model strings should return False.
        """
        # Act & Assert
        assert is_qwen_model(model="gpt-4o") is False
        assert is_qwen_model(model="claude-3-opus") is False

    @pytest.mark.ai
    def test_is_qwen_model__returns_false__for_none(self) -> None:
        """
        Purpose: Verify is_qwen_model returns False for None input.
        Why this matters: Should handle None gracefully.
        """
        # Act
        result = is_qwen_model(model=None)

        # Assert
        assert result is False


# Helper Function Tests - append_qwen_forced_tool_call_instruction
class TestAppendQwenForcedToolCallInstruction:
    @pytest.mark.ai
    def test_append_instruction__modifies_last_user_message(
        self, sample_messages: LanguageModelMessages
    ) -> None:
        """
        Purpose: Verify instruction is appended to last user message.
        Why this matters: Qwen needs explicit instructions in user message for tool calls.
        """
        # Arrange
        instruction = "Test instruction"

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=sample_messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert
        result_list = list(result)
        assert len(result_list) == 2
        assert result_list[1].content == "Search for documentsTest instruction"

    @pytest.mark.ai
    def test_append_instruction__preserves_system_message(
        self, sample_messages: LanguageModelMessages
    ) -> None:
        """
        Purpose: Verify system message is not modified.
        Why this matters: Only user messages should be modified.
        """
        # Arrange
        instruction = "Test instruction"

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=sample_messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert
        result_list = list(result)
        assert result_list[0].content == "You are a helpful assistant."

    @pytest.mark.ai
    def test_append_instruction__finds_last_user_message__when_multiple_exist(
        self,
    ) -> None:
        """
        Purpose: Verify instruction is appended to the last user message when multiple exist.
        Why this matters: Should modify most recent user message.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="First question"),
                LanguageModelAssistantMessage(content="First answer"),
                LanguageModelUserMessage(content="Second question"),
            ]
        )
        instruction = " [INSTRUCTION]"

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert
        result_list = list(result)
        assert result_list[0].content == "First question"  # Not modified
        assert result_list[1].content == "First answer"  # Not modified
        assert result_list[2].content == "Second question [INSTRUCTION]"  # Modified

    @pytest.mark.ai
    def test_append_instruction__handles_no_user_messages(self) -> None:
        """
        Purpose: Verify graceful handling when no user messages exist.
        Why this matters: Should not fail when there are no user messages.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[LanguageModelSystemMessage(content="System prompt")]
        )
        instruction = "Test instruction"

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert
        result_list = list(result)
        assert len(result_list) == 1
        assert result_list[0].content == "System prompt"  # Unchanged

    @pytest.mark.ai
    def test_append_instruction__returns_new_messages_instance(
        self, sample_messages: LanguageModelMessages
    ) -> None:
        """
        Purpose: Verify original messages are not mutated.
        Why this matters: Immutability prevents side effects.
        """
        # Arrange
        instruction = "Test instruction"
        original_content = list(sample_messages)[1].content

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=sample_messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert
        assert result is not sample_messages
        assert list(sample_messages)[1].content == original_content  # Original unchanged


# Middleware Initialization Tests
class TestQwenForcedToolCallMiddlewareInit:
    @pytest.mark.ai
    def test_middleware__initializes__with_loop_runner_and_instruction(
        self, mock_inner_runner: AsyncMock
    ) -> None:
        """
        Purpose: Verify middleware initializes with provided parameters.
        Why this matters: Proper initialization is required for middleware operations.
        """
        # Arrange
        instruction = "Custom instruction"

        # Act
        middleware = QwenForcedToolCallMiddleware(
            loop_runner=mock_inner_runner,
            qwen_forced_tool_call_prompt_instruction=instruction,
        )

        # Assert
        assert middleware._loop_runner is mock_inner_runner
        assert middleware._qwen_forced_tool_call_prompt_instruction == instruction


# Middleware Call Tests
class TestQwenForcedToolCallMiddlewareCall:
    @pytest.mark.ai
    async def test_middleware__appends_instruction__when_tool_choices_and_first_iteration(
        self,
        mock_inner_runner: AsyncMock,
        sample_messages: LanguageModelMessages,
        sample_tool_choices: list[ChatCompletionNamedToolChoiceParam],
        mock_language_model: LanguageModelInfo,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify instruction is appended when tool_choices present on first iteration.
        Why this matters: Qwen models need explicit tool call instruction in user message.
        """
        # Arrange
        instruction = " [FORCE TOOL]"
        middleware = QwenForcedToolCallMiddleware(
            loop_runner=mock_inner_runner,
            qwen_forced_tool_call_prompt_instruction=instruction,
        )

        # Act
        await middleware(
            iteration_index=0,
            messages=sample_messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=sample_tool_choices,
        )

        # Assert
        mock_inner_runner.assert_called_once()
        call_kwargs = mock_inner_runner.call_args.kwargs
        modified_messages = list(call_kwargs["messages"])
        assert modified_messages[1].content == "Search for documents [FORCE TOOL]"

    @pytest.mark.ai
    async def test_middleware__does_not_append_instruction__when_no_tool_choices(
        self,
        mock_inner_runner: AsyncMock,
        sample_messages: LanguageModelMessages,
        mock_language_model: LanguageModelInfo,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify instruction is not appended when no tool_choices.
        Why this matters: Instruction only needed when forcing tool calls.
        """
        # Arrange
        instruction = " [FORCE TOOL]"
        middleware = QwenForcedToolCallMiddleware(
            loop_runner=mock_inner_runner,
            qwen_forced_tool_call_prompt_instruction=instruction,
        )

        # Act
        await middleware(
            iteration_index=0,
            messages=sample_messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=[],
        )

        # Assert
        mock_inner_runner.assert_called_once()
        call_kwargs = mock_inner_runner.call_args.kwargs
        modified_messages = list(call_kwargs["messages"])
        assert modified_messages[1].content == "Search for documents"  # Unchanged

    @pytest.mark.ai
    async def test_middleware__does_not_append_instruction__when_not_first_iteration(
        self,
        mock_inner_runner: AsyncMock,
        sample_messages: LanguageModelMessages,
        sample_tool_choices: list[ChatCompletionNamedToolChoiceParam],
        mock_language_model: LanguageModelInfo,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify instruction is not appended on subsequent iterations.
        Why this matters: Instruction only needed on first iteration.
        """
        # Arrange
        instruction = " [FORCE TOOL]"
        middleware = QwenForcedToolCallMiddleware(
            loop_runner=mock_inner_runner,
            qwen_forced_tool_call_prompt_instruction=instruction,
        )

        # Act
        await middleware(
            iteration_index=1,
            messages=sample_messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=sample_tool_choices,
        )

        # Assert
        mock_inner_runner.assert_called_once()
        call_kwargs = mock_inner_runner.call_args.kwargs
        modified_messages = list(call_kwargs["messages"])
        assert modified_messages[1].content == "Search for documents"  # Unchanged

    @pytest.mark.ai
    async def test_middleware__does_not_append_instruction__when_no_messages(
        self,
        mock_inner_runner: AsyncMock,
        sample_tool_choices: list[ChatCompletionNamedToolChoiceParam],
        mock_language_model: LanguageModelInfo,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify middleware handles missing messages gracefully.
        Why this matters: Should not fail when messages are not provided.
        """
        # Arrange
        instruction = " [FORCE TOOL]"
        middleware = QwenForcedToolCallMiddleware(
            loop_runner=mock_inner_runner,
            qwen_forced_tool_call_prompt_instruction=instruction,
        )

        # Act - messages not provided (will be None in kwargs.get)
        await middleware(
            iteration_index=0,
            messages=LanguageModelMessages(root=[]),
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=sample_tool_choices,
        )

        # Assert
        mock_inner_runner.assert_called_once()

    @pytest.mark.ai
    async def test_middleware__returns_inner_runner_response(
        self,
        mock_inner_runner: AsyncMock,
        sample_messages: LanguageModelMessages,
        mock_language_model: LanguageModelInfo,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify middleware returns the response from inner runner.
        Why this matters: Response should pass through unchanged.
        """
        # Arrange
        expected_response = create_stream_response(text="Test response")
        mock_inner_runner.return_value = expected_response
        middleware = QwenForcedToolCallMiddleware(
            loop_runner=mock_inner_runner,
            qwen_forced_tool_call_prompt_instruction="instruction",
        )

        # Act
        result = await middleware(
            iteration_index=0,
            messages=sample_messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result is expected_response

    @pytest.mark.ai
    async def test_middleware__uses_default_instruction_constant(self) -> None:
        """
        Purpose: Verify the default instruction constant is properly defined.
        Why this matters: Default instruction should guide Qwen to make tool calls.
        """
        # Assert
        assert "tool call" in QWEN_FORCED_TOOL_CALL_PROMPT_INSTRUCTION.lower()
        assert "<tool_call>" in QWEN_FORCED_TOOL_CALL_PROMPT_INSTRUCTION
        assert "</tool_call>" in QWEN_FORCED_TOOL_CALL_PROMPT_INSTRUCTION

    @pytest.mark.ai
    async def test_middleware__passes_through_all_kwargs__to_inner_runner(
        self,
        mock_inner_runner: AsyncMock,
        sample_messages: LanguageModelMessages,
        mock_language_model: LanguageModelInfo,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify all kwargs are passed to inner runner.
        Why this matters: Middleware should not drop any parameters.
        """
        # Arrange
        middleware = QwenForcedToolCallMiddleware(
            loop_runner=mock_inner_runner,
            qwen_forced_tool_call_prompt_instruction="instruction",
        )
        mock_tool = MagicMock()
        other_options = {"temperature": 0.7}

        # Act
        await middleware(
            iteration_index=2,
            messages=sample_messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tools=[mock_tool],
            other_options=other_options,
        )

        # Assert
        mock_inner_runner.assert_called_once()
        call_kwargs = mock_inner_runner.call_args.kwargs
        assert call_kwargs["iteration_index"] == 2
        assert call_kwargs["model"] is mock_language_model
        assert call_kwargs["streaming_handler"] is mock_streaming_handler
        assert call_kwargs["tools"] == [mock_tool]
        assert call_kwargs["other_options"] == other_options
