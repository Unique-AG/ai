"""
Tests for QwenLoopIterationRunner and Qwen helper functions.

This file contains tests for the Qwen-specific loop iteration runner
and its helper functions for message manipulation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.chat import ChatCompletionNamedToolChoiceParam

from unique_toolkit.agentic.loop_runner.runners.qwen import (
    QWEN_FORCED_TOOL_CALL_INSTRUCTION,
    QWEN_LAST_ITERATION_INSTRUCTION,
    QwenLoopIterationRunner,
    is_qwen_model,
)
from unique_toolkit.agentic.loop_runner.runners.qwen.helpers import (
    append_qwen_forced_tool_call_instruction,
    append_qwen_last_iteration_assistant_message,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


# Helper functions
def create_stream_response(
    text: str = "Response text",
    tool_calls: list[LanguageModelFunction] | None = None,
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
        tool_calls=tool_calls,
    )


def create_mock_tool(name: str = "TestTool") -> MagicMock:
    """Helper function to create a mock tool."""
    tool = MagicMock()
    tool.name = name
    return tool


# Fixtures
@pytest.fixture
def mock_streaming_handler() -> MagicMock:
    """Provide a mock streaming handler."""
    handler = MagicMock()
    handler.complete_with_references_async = AsyncMock()
    return handler


@pytest.fixture
def mock_chat_service() -> MagicMock:
    """Provide a mock chat service."""
    service = MagicMock()
    service.modify_assistant_message = MagicMock()
    return service


@pytest.fixture
def mock_qwen_model() -> LanguageModelInfo:
    """Provide a Qwen language model info for tests."""
    return LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)


@pytest.fixture
def qwen_runner(mock_chat_service: MagicMock) -> QwenLoopIterationRunner:
    """Provide a QwenLoopIterationRunner instance for testing."""
    return QwenLoopIterationRunner(
        qwen_forced_tool_call_instruction=QWEN_FORCED_TOOL_CALL_INSTRUCTION,
        qwen_last_iteration_instruction=QWEN_LAST_ITERATION_INSTRUCTION,
        max_loop_iterations=5,
        chat_service=mock_chat_service,
    )


@pytest.fixture
def base_messages() -> LanguageModelMessages:
    """Provide base messages for testing."""
    return LanguageModelMessages(
        root=[
            LanguageModelSystemMessage(content="You are a helpful assistant."),
            LanguageModelUserMessage(content="Hello, search for something"),
        ]
    )


# Tests for is_qwen_model helper
class TestIsQwenModel:
    @pytest.mark.ai
    def test_is_qwen_model__returns_true__for_qwen_language_model_info(self) -> None:
        """
        Purpose: Verify is_qwen_model returns True for Qwen LanguageModelInfo.
        Why this matters: Correct model detection is required for Qwen-specific handling.
        """
        # Arrange
        model = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)

        # Act
        result = is_qwen_model(model=model)

        # Assert
        assert result is True

    @pytest.mark.ai
    def test_is_qwen_model__returns_true__for_qwen_string(self) -> None:
        """
        Purpose: Verify is_qwen_model returns True for Qwen string.
        Why this matters: String model names should also be detected.
        """
        # Act & Assert
        assert is_qwen_model(model="qwen-3") is True
        assert is_qwen_model(model="Qwen-2.5") is True
        assert is_qwen_model(model="QWEN") is True
        assert is_qwen_model(model="litellm/qwen3") is True

    @pytest.mark.ai
    def test_is_qwen_model__returns_false__for_non_qwen_model(self) -> None:
        """
        Purpose: Verify is_qwen_model returns False for non-Qwen models.
        Why this matters: Non-Qwen models should not get Qwen-specific handling.
        """
        # Arrange
        gpt_model = LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0513
        )

        # Act & Assert
        assert is_qwen_model(model=gpt_model) is False
        assert is_qwen_model(model="gpt-4") is False
        assert is_qwen_model(model="claude-3") is False

    @pytest.mark.ai
    def test_is_qwen_model__returns_false__for_none(self) -> None:
        """
        Purpose: Verify is_qwen_model returns False for None.
        Why this matters: None should be handled gracefully.
        """
        # Act & Assert
        assert is_qwen_model(model=None) is False


# Tests for append_qwen_forced_tool_call_instruction helper
class TestAppendQwenForcedToolCallInstruction:
    @pytest.mark.ai
    def test_append_instruction__appends_to_last_user_message(self) -> None:
        """
        Purpose: Verify instruction is appended to last user message.
        Why this matters: Qwen needs tool call instructions in user message.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[
                LanguageModelSystemMessage(content="System prompt"),
                LanguageModelUserMessage(content="Search for docs"),
            ]
        )
        instruction = "Call the SearchTool"

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert
        result_list = list(result)
        assert len(result_list) == 2
        assert result_list[1].content == "Search for docs\nCall the SearchTool"

    @pytest.mark.ai
    def test_append_instruction__finds_last_user_message__when_not_at_end(self) -> None:
        """
        Purpose: Verify instruction appends to last user message even if not at end.
        Why this matters: Messages may have assistant responses after user message.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="First question"),
                LanguageModelAssistantMessage(content="First answer"),
                LanguageModelUserMessage(content="Second question"),
                LanguageModelAssistantMessage(content="Second answer"),
            ]
        )
        instruction = "Call the tool"

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert
        result_list = list(result)
        assert result_list[2].content == "Second question\nCall the tool"
        # First user message unchanged
        assert result_list[0].content == "First question"

    @pytest.mark.ai
    def test_append_instruction__preserves_original_messages(self) -> None:
        """
        Purpose: Verify original messages are not modified.
        Why this matters: Messages should be copied, not mutated.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Original content")]
        )
        instruction = "Added instruction"

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert - original unchanged
        assert list(messages)[0].content == "Original content"
        # Result has modification
        assert list(result)[0].content == "Original content\nAdded instruction"

    @pytest.mark.ai
    def test_append_instruction__handles_no_user_messages(self) -> None:
        """
        Purpose: Verify handling when no user messages exist.
        Why this matters: Edge case should not crash.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[LanguageModelSystemMessage(content="System only")]
        )
        instruction = "Call tool"

        # Act
        result = append_qwen_forced_tool_call_instruction(
            messages=messages,
            forced_tool_call_instruction=instruction,
        )

        # Assert - returns unchanged messages
        result_list = list(result)
        assert len(result_list) == 1
        assert result_list[0].content == "System only"


# Tests for append_qwen_last_iteration_assistant_message helper
class TestAppendQwenLastIterationAssistantMessage:
    @pytest.mark.ai
    def test_append_assistant_message__adds_at_end(self) -> None:
        """
        Purpose: Verify assistant message is appended at end.
        Why this matters: Qwen needs instruction to stop tool calls.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="User question")]
        )
        instruction = "No more tool calls allowed"

        # Act
        result = append_qwen_last_iteration_assistant_message(
            messages=messages,
            last_iteration_instruction=instruction,
        )

        # Assert
        result_list = list(result)
        assert len(result_list) == 2
        assert result_list[1].role == LanguageModelMessageRole.ASSISTANT
        assert result_list[1].content == "No more tool calls allowed"

    @pytest.mark.ai
    def test_append_assistant_message__preserves_existing_messages(self) -> None:
        """
        Purpose: Verify existing messages are preserved.
        Why this matters: Original conversation should remain intact.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[
                LanguageModelSystemMessage(content="System"),
                LanguageModelUserMessage(content="User"),
                LanguageModelAssistantMessage(content="Assistant"),
            ]
        )
        instruction = "Final instruction"

        # Act
        result = append_qwen_last_iteration_assistant_message(
            messages=messages,
            last_iteration_instruction=instruction,
        )

        # Assert
        result_list = list(result)
        assert len(result_list) == 4
        assert result_list[0].content == "System"
        assert result_list[1].content == "User"
        assert result_list[2].content == "Assistant"
        assert result_list[3].content == "Final instruction"


# Tests for QwenLoopIterationRunner initialization
class TestQwenLoopIterationRunnerInit:
    @pytest.mark.ai
    def test_runner__initializes__with_all_parameters(
        self, mock_chat_service: MagicMock
    ) -> None:
        """
        Purpose: Verify runner initializes with all parameters.
        Why this matters: Proper initialization is required for runner operations.
        """
        # Act
        runner = QwenLoopIterationRunner(
            qwen_forced_tool_call_instruction="Custom instruction {TOOL_NAME}",
            qwen_last_iteration_instruction="Custom last instruction",
            max_loop_iterations=10,
            chat_service=mock_chat_service,
        )

        # Assert
        assert (
            runner._qwen_forced_tool_call_instruction
            == "Custom instruction {TOOL_NAME}"
        )
        assert runner._qwen_last_iteration_instruction == "Custom last instruction"
        assert runner._max_loop_iterations == 10
        assert runner._chat_service == mock_chat_service

    @pytest.mark.ai
    def test_runner__uses_default_instructions__from_constants(
        self, mock_chat_service: MagicMock
    ) -> None:
        """
        Purpose: Verify default instructions are available.
        Why this matters: Default instructions should be usable.
        """
        # Act
        runner = QwenLoopIterationRunner(
            qwen_forced_tool_call_instruction=QWEN_FORCED_TOOL_CALL_INSTRUCTION,
            qwen_last_iteration_instruction=QWEN_LAST_ITERATION_INSTRUCTION,
            max_loop_iterations=5,
            chat_service=mock_chat_service,
        )

        # Assert
        assert "MUST call the tool" in runner._qwen_forced_tool_call_instruction
        assert (
            "maximum number of loop iteration"
            in runner._qwen_last_iteration_instruction
        )


# Tests for QwenLoopIterationRunner routing
class TestQwenLoopIterationRunnerRouting:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.run_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_forced_tools__when_tool_choices_on_first_iteration(
        self,
        mock_run_forced: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify forced tools is called with tool_choices on first iteration.
        Why this matters: Qwen needs special handling for forced tools.
        """
        # Arrange
        mock_run_forced.return_value = create_stream_response()
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]

        # Act
        await qwen_runner(
            iteration_index=0,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
        )

        # Assert
        mock_run_forced.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_last_iteration",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_last_iteration__when_at_max_iterations(
        self,
        mock_last: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify last iteration handler is called at max iterations.
        Why this matters: Qwen needs assistant message for last iteration.
        """
        # Arrange
        mock_last.return_value = create_stream_response()

        # Act - iteration_index is 4 (0-based), max is 5
        await qwen_runner(
            iteration_index=4,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        mock_last.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_normal__for_middle_iterations(
        self,
        mock_normal: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify normal iteration is called for middle iterations.
        Why this matters: Normal iterations should use standard handling.
        """
        # Arrange
        mock_normal.return_value = create_stream_response()

        # Act
        await qwen_runner(
            iteration_index=2,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        mock_normal.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_normal__when_tool_choices_not_first_iteration(
        self,
        mock_normal: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify normal iteration when tool_choices but not first iteration.
        Why this matters: Forced tools only apply on first iteration.
        """
        # Arrange
        mock_normal.return_value = create_stream_response()
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool"}}
        ]

        # Act
        await qwen_runner(
            iteration_index=1,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
        )

        # Assert
        mock_normal.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_normal__when_empty_tool_choices(
        self,
        mock_normal: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify empty tool_choices routes to normal.
        Why this matters: Empty list should be treated as no tool_choices.
        """
        # Arrange
        mock_normal.return_value = create_stream_response()

        # Act
        await qwen_runner(
            iteration_index=0,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=[],
        )

        # Assert
        mock_normal.assert_called_once()


# Tests for Qwen-specific forced tools handling
class TestQwenForcedToolsIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.run_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__provides_prepare_callback__to_run_forced_tools(
        self,
        mock_run_forced: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify prepare_loop_runner_kwargs callback is provided.
        Why this matters: Qwen needs message modification per tool choice.
        """
        # Arrange
        mock_run_forced.return_value = create_stream_response()
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]

        # Act
        await qwen_runner(
            iteration_index=0,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
        )

        # Assert
        call_kwargs = mock_run_forced.call_args.kwargs
        assert call_kwargs.get("prepare_loop_runner_kwargs") is not None

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.run_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__prepare_callback__modifies_messages_with_instruction(
        self,
        mock_run_forced: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify prepare callback adds tool instruction to messages.
        Why this matters: Qwen models need explicit tool call instruction.
        """
        # Arrange
        mock_run_forced.return_value = create_stream_response()
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]

        # Act
        await qwen_runner(
            iteration_index=0,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
        )

        # Assert - get the prepare callback and test it
        call_kwargs = mock_run_forced.call_args.kwargs
        prepare_fn = call_kwargs["prepare_loop_runner_kwargs"]

        # Simulate calling prepare
        from unique_toolkit.agentic.loop_runner.base import _LoopIterationRunnerKwargs

        test_kwargs = _LoopIterationRunnerKwargs(
            iteration_index=0,
            streaming_handler=mock_streaming_handler,
            messages=base_messages,
            model=mock_qwen_model,
        )
        result = prepare_fn("SearchTool", test_kwargs)

        # Check that messages were modified
        result_messages = list(result["messages"])
        last_user_msg = None
        for msg in reversed(result_messages):
            if msg.role == LanguageModelMessageRole.USER:
                last_user_msg = msg
                break

        assert last_user_msg is not None
        assert "SearchTool" in last_user_msg.content


# Tests for Qwen-specific last iteration handling
class TestQwenLastIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_last_iteration",
        new_callable=AsyncMock,
    )
    async def test_last_iteration__appends_assistant_message(
        self,
        mock_last: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify assistant message is appended for last iteration.
        Why this matters: Qwen needs explicit instruction to stop tool calls.
        """
        # Arrange
        mock_last.return_value = create_stream_response()

        # Act
        await qwen_runner(
            iteration_index=4,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        call_kwargs = mock_last.call_args.kwargs
        messages = call_kwargs["messages"]
        messages_list = list(messages)

        # Last message should be assistant with instruction
        last_msg = messages_list[-1]
        assert last_msg.role == LanguageModelMessageRole.ASSISTANT
        assert "maximum number of loop iteration" in last_msg.content


# Tests for _process_response
class TestQwenProcessResponse:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_process_response__clears_tool_call_only_response(
        self,
        mock_normal: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        Purpose: Verify </tool_call> only response is cleared.
        Why this matters: Invalid response should be handled gracefully.
        """
        # Arrange
        mock_normal.return_value = create_stream_response(text="</tool_call>")

        # Act
        result = await qwen_runner(
            iteration_index=1,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result.message.text == ""
        mock_chat_service.modify_assistant_message.assert_called_once_with(content="")

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_process_response__clears_response__with_whitespace(
        self,
        mock_normal: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        Purpose: Verify </tool_call> with whitespace is also cleared.
        Why this matters: Whitespace variations should be handled.
        """
        # Arrange
        mock_normal.return_value = create_stream_response(text="  </tool_call>  \n")

        # Act
        result = await qwen_runner(
            iteration_index=1,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result.message.text == ""
        mock_chat_service.modify_assistant_message.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_process_response__preserves_normal_response(
        self,
        mock_normal: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        Purpose: Verify normal responses are not modified.
        Why this matters: Valid responses should pass through unchanged.
        """
        # Arrange
        mock_normal.return_value = create_stream_response(text="Normal response text")

        # Act
        result = await qwen_runner(
            iteration_index=1,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result.message.text == "Normal response text"
        mock_chat_service.modify_assistant_message.assert_not_called()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_process_response__preserves_response_with_tool_call_in_content(
        self,
        mock_normal: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
        mock_chat_service: MagicMock,
    ) -> None:
        """
        Purpose: Verify response containing </tool_call> with other content is preserved.
        Why this matters: Only pure </tool_call> responses should be cleared.
        """
        # Arrange
        mock_normal.return_value = create_stream_response(
            text="Some text before </tool_call>"
        )

        # Act
        result = await qwen_runner(
            iteration_index=1,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result.message.text == "Some text before </tool_call>"
        mock_chat_service.modify_assistant_message.assert_not_called()


# Edge case tests
class TestQwenLoopIterationRunnerEdgeCases:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.run_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    async def test_forced_tools_priority__over_last_iteration(
        self,
        mock_run_forced: AsyncMock,
        mock_chat_service: MagicMock,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify forced tools takes priority when both conditions match.
        Why this matters: On iteration 0 with max=1, forced tools should run.
        """
        # Arrange
        runner = QwenLoopIterationRunner(
            qwen_forced_tool_call_instruction=QWEN_FORCED_TOOL_CALL_INSTRUCTION,
            qwen_last_iteration_instruction=QWEN_LAST_ITERATION_INSTRUCTION,
            max_loop_iterations=1,
            chat_service=mock_chat_service,
        )
        tool_call = LanguageModelFunction(id="call_1", name="SearchTool", arguments={})
        mock_run_forced.return_value = create_stream_response(tool_calls=[tool_call])

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]

        # Act
        result = await runner(
            iteration_index=0,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
        )

        # Assert - forced tools was called
        mock_run_forced.assert_called_once()
        assert result.tool_calls is not None

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.run_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__handles_none_tool_choices(
        self,
        mock_run_forced: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify None tool_choices is handled as empty.
        Why this matters: tool_choices may be None instead of empty list.
        """
        # Arrange - don't set tool_choices at all

        # Act
        with patch(
            "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.handle_normal_iteration",
            new_callable=AsyncMock,
        ) as mock_normal:
            mock_normal.return_value = create_stream_response()
            await qwen_runner(
                iteration_index=0,
                messages=base_messages,
                model=mock_qwen_model,
                streaming_handler=mock_streaming_handler,
                # No tool_choices - defaults to None
            )

            # Assert - should go to normal, not forced
            mock_normal.assert_called_once()
            mock_run_forced.assert_not_called()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.qwen.qwen_runner.run_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__merges_tool_calls_from_responses(
        self,
        mock_run_forced: AsyncMock,
        qwen_runner: QwenLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_qwen_model: LanguageModelInfo,
        base_messages: LanguageModelMessages,
    ) -> None:
        """
        Purpose: Verify tool calls are returned from merged responses.
        Why this matters: Multiple forced tools should produce combined result.
        """
        # Arrange
        tool_call_1 = LanguageModelFunction(id="call_1", name="Tool1", arguments={})
        tool_call_2 = LanguageModelFunction(id="call_2", name="Tool2", arguments={})
        mock_run_forced.return_value = create_stream_response(
            tool_calls=[tool_call_1, tool_call_2]
        )

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]

        # Act
        result = await qwen_runner(
            iteration_index=0,
            messages=base_messages,
            model=mock_qwen_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
        )

        # Assert
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 2


# Test default constants
class TestQwenConstants:
    @pytest.mark.ai
    def test_forced_tool_call_instruction__contains_placeholder(self) -> None:
        """
        Purpose: Verify instruction template has TOOL_NAME placeholder.
        Why this matters: Placeholder is needed for tool name injection.
        """
        assert "{TOOL_NAME}" in QWEN_FORCED_TOOL_CALL_INSTRUCTION

    @pytest.mark.ai
    def test_forced_tool_call_instruction__contains_tool_call_tag(self) -> None:
        """
        Purpose: Verify instruction mentions <tool_call> tag.
        Why this matters: Qwen uses this tag format for tool calls.
        """
        assert "<tool_call>" in QWEN_FORCED_TOOL_CALL_INSTRUCTION

    @pytest.mark.ai
    def test_last_iteration_instruction__mentions_no_tool_calls(self) -> None:
        """
        Purpose: Verify last iteration instruction is about stopping tools.
        Why this matters: Instruction should clearly state no more tool calls.
        """
        assert "tool" in QWEN_LAST_ITERATION_INSTRUCTION.lower()
