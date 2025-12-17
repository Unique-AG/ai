"""
Tests for BasicLoopIterationRunner.

This file contains tests for the BasicLoopIterationRunner class which manages
the iteration flow for agentic tool loops.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.chat import ChatCompletionNamedToolChoiceParam

from unique_toolkit.agentic.loop_runner.runners.basic import (
    BasicLoopIterationRunner,
    BasicLoopIterationRunnerConfig,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelUserMessage,
)


# Fixtures
@pytest.fixture
def basic_config() -> BasicLoopIterationRunnerConfig:
    """Provide a basic config for tests."""
    return BasicLoopIterationRunnerConfig(max_loop_iterations=5)


@pytest.fixture
def runner(basic_config: BasicLoopIterationRunnerConfig) -> BasicLoopIterationRunner:
    """Provide a BasicLoopIterationRunner instance for testing."""
    return BasicLoopIterationRunner(config=basic_config)


@pytest.fixture
def mock_streaming_handler() -> MagicMock:
    """Provide a mock streaming handler."""
    handler = MagicMock()
    handler.complete_with_references_async = AsyncMock()
    return handler


@pytest.fixture
def mock_language_model() -> LanguageModelInfo:
    """Provide a language model info for tests."""
    return LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0513)


@pytest.fixture
def mock_qwen_model() -> LanguageModelInfo:
    """Provide a Qwen language model info for tests."""
    return LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)


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


def create_mock_tool() -> MagicMock:
    """Helper function to create a mock tool."""
    tool = MagicMock()
    tool.name = "SearchTool"
    return tool


# Config Tests
class TestBasicLoopIterationRunnerConfig:
    @pytest.mark.ai
    def test_config__creates_valid_instance__with_max_iterations(self) -> None:
        """
        Purpose: Verify config can be created with max_loop_iterations.
        Why this matters: Config is required for runner initialization.
        """
        # Act
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=10)

        # Assert
        assert config.max_loop_iterations == 10


# Initialization Tests
class TestBasicLoopIterationRunnerInit:
    @pytest.mark.ai
    def test_runner__initializes__with_config(
        self, basic_config: BasicLoopIterationRunnerConfig
    ) -> None:
        """
        Purpose: Verify runner initializes with provided config.
        Why this matters: Proper initialization is required for runner operations.
        """
        # Act
        runner = BasicLoopIterationRunner(config=basic_config)

        # Assert
        assert runner._config == basic_config
        assert runner._config.max_loop_iterations == 5


# Call Method Tests - Route Selection
class TestBasicLoopIterationRunnerCall:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_normal_iteration__when_no_tool_choices(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify normal iteration is called when no tool_choices.
        Why this matters: Default behavior should handle regular iterations.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )

        # Act
        result = await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result is not None
        mock_stream.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_last_iteration__when_at_max_iterations(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify last iteration handler is called at max iterations.
        Why this matters: Final iteration should remove tools to force text response.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )

        # Act - iteration_index is 4 (0-based), max is 5
        result = await runner(
            iteration_index=4,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result is not None
        mock_stream.assert_called_once()
        # Verify tools=None was passed for last iteration
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") is None

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_forced_tools__when_tool_choices_on_first_iteration(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify forced tools iteration is called with tool_choices on first iteration.
        Why this matters: Forced tool calls should be handled specially.
        """
        # Arrange
        mock_stream.return_value = create_stream_response(
            tool_calls=[LanguageModelFunction(name="SearchTool", arguments={})]
        )
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Search for docs")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]
        mock_tool = create_mock_tool()

        # Act
        result = await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[mock_tool],
        )

        # Assert
        assert result is not None
        mock_stream.assert_called()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_normal__when_tool_choices_not_first_iteration(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify normal iteration is called when tool_choices present but not first iteration.
        Why this matters: Forced tools only apply to first iteration.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]

        # Act - iteration_index is 1, not 0
        result = await runner(
            iteration_index=1,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
        )

        # Assert
        assert result is not None
        mock_stream.assert_called_once()


# Forced Tools Iteration Tests
class TestForcedToolsIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__merges_tool_calls__from_multiple_responses(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify tool calls are merged from multiple forced tool responses.
        Why this matters: Multiple forced tools should produce combined result.
        """
        # Arrange
        tool_call_1 = LanguageModelFunction(
            id="call_1", name="SearchTool", arguments={}
        )
        tool_call_2 = LanguageModelFunction(id="call_2", name="OtherTool", arguments={})

        mock_stream.side_effect = [
            create_stream_response(tool_calls=[tool_call_1]),
            create_stream_response(tool_calls=[tool_call_2]),
        ]

        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Search")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}},
            {"type": "function", "function": {"name": "OtherTool"}},
        ]
        mock_search_tool = MagicMock()
        mock_search_tool.name = "SearchTool"
        mock_other_tool = MagicMock()
        mock_other_tool.name = "OtherTool"

        # Act
        result = await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[mock_search_tool, mock_other_tool],
        )

        # Assert
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].name == "SearchTool"
        assert result.tool_calls[1].name == "OtherTool"

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__merges_references__from_multiple_responses(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify references are merged from multiple forced tool responses.
        Why this matters: All references from tools should be collected.
        """
        # Arrange
        ref_1 = ContentReference(
            id="ref_1",
            name="ref_1",
            sequence_number=1,
            source="Source 1",
            source_id="src_1",
            url="https://example.com",
        )
        ref_2 = ContentReference(
            id="ref_2",
            name="ref_2",
            sequence_number=2,
            source="Source 2",
            source_id="src_2",
            url="https://example.com",
        )

        mock_stream.side_effect = [
            create_stream_response(references=[ref_1]),
            create_stream_response(references=[ref_2]),
        ]

        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Search")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]
        mock_tool_1 = MagicMock()
        mock_tool_1.name = "Tool1"
        mock_tool_2 = MagicMock()
        mock_tool_2.name = "Tool2"

        # Act
        result = await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[mock_tool_1, mock_tool_2],
        )

        # Assert
        assert len(result.message.references) == 2

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__limits_tools_to_matching_tool(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify each tool choice only sends the matching tool.
        Why this matters: Limiting tools prevents model from calling wrong tool.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Search")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]
        mock_search_tool = MagicMock()
        mock_search_tool.name = "SearchTool"
        mock_other_tool = MagicMock()
        mock_other_tool.name = "OtherTool"

        # Act
        await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[mock_search_tool, mock_other_tool],
        )

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") == [mock_search_tool]

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__handles_missing_tool(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify graceful handling when requested tool is not in available tools.
        Why this matters: Should not fail when tool_choice refers to unknown tool.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Search")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "UnknownTool"}}
        ]
        mock_search_tool = MagicMock()
        mock_search_tool.name = "SearchTool"

        # Act
        await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[mock_search_tool],
        )

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") is None

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__returns_none_tool_calls__when_no_tools_called(
        self,
        mock_stream: AsyncMock,
        runner: BasicLoopIterationRunner,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify tool_calls is None when no tool calls in responses.
        Why this matters: Empty tool calls should be represented as None.
        """
        # Arrange
        mock_stream.return_value = create_stream_response(tool_calls=None)
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Search")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]
        mock_search_tool = MagicMock()
        mock_search_tool.name = "SearchTool"

        # Act
        result = await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[mock_search_tool],
        )

        # Assert
        assert result.tool_calls is None


# Additional Config Tests
class TestBasicLoopIterationRunnerConfigValidation:
    @pytest.mark.ai
    def test_config__creates_instance__with_different_max_iterations(self) -> None:
        """
        Purpose: Verify config works with various max_loop_iterations values.
        Why this matters: Different use cases require different iteration limits.
        """
        # Act & Assert
        config_1 = BasicLoopIterationRunnerConfig(max_loop_iterations=1)
        assert config_1.max_loop_iterations == 1

        config_10 = BasicLoopIterationRunnerConfig(max_loop_iterations=10)
        assert config_10.max_loop_iterations == 10

        config_100 = BasicLoopIterationRunnerConfig(max_loop_iterations=100)
        assert config_100.max_loop_iterations == 100

    @pytest.mark.ai
    def test_config__raises_validation_error__with_invalid_type(self) -> None:
        """
        Purpose: Verify config rejects invalid max_loop_iterations types.
        Why this matters: Type safety ensures correct configuration.
        """
        # Act & Assert
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BasicLoopIterationRunnerConfig(max_loop_iterations="invalid")  # type: ignore[arg-type]


# Edge Case Tests
class TestBasicLoopIterationRunnerEdgeCases:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_normal__when_tool_choices_is_empty_list(
        self,
        mock_stream: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify empty tool_choices list routes to normal iteration.
        Why this matters: Empty list should be treated same as no tool_choices.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=5)
        runner = BasicLoopIterationRunner(config=config)
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )

        # Act - pass empty tool_choices list
        result = await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=[],  # Empty list
        )

        # Assert - should route to normal, not forced tools
        assert result is not None
        mock_stream.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_last_iteration__when_max_iterations_is_one(
        self,
        mock_stream: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify first iteration is also last when max_iterations=1.
        Why this matters: Edge case where only one iteration is allowed.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=1)
        runner = BasicLoopIterationRunner(config=config)
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )

        # Act - iteration_index 0 is the last (and only) iteration
        result = await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result is not None
        mock_stream.assert_called_once()
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") is None  # Last iteration removes tools

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__forced_tools_takes_priority__over_last_iteration(
        self,
        mock_stream: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify forced tools takes priority when both conditions match.
        Why this matters: On iteration 0 with max=1, forced tools should run first.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=1)
        runner = BasicLoopIterationRunner(config=config)

        tool_call = LanguageModelFunction(id="call_1", name="SearchTool", arguments={})
        mock_stream.return_value = create_stream_response(tool_calls=[tool_call])

        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Search")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]
        mock_tool = create_mock_tool()

        # Act - iteration 0 with max=1, but with tool_choices
        result = await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[mock_tool],
        )

        # Assert - should have tool calls (forced tools ran, not last iteration)
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__routes_to_normal__for_middle_iterations(
        self,
        mock_stream: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify middle iterations route to normal handler.
        Why this matters: Iterations between 0 and max-1 should be normal.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=10)
        runner = BasicLoopIterationRunner(config=config)
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )
        mock_tool = create_mock_tool()

        # Act & Assert - test multiple middle iterations
        for iteration in [1, 2, 5, 8]:
            mock_stream.reset_mock()
            result = await runner(
                iteration_index=iteration,
                messages=messages,
                model=mock_language_model,
                streaming_handler=mock_streaming_handler,
                tools=[mock_tool],
            )
            assert result is not None
            mock_stream.assert_called_once()
            # Normal iteration should preserve tools
            call_kwargs = mock_stream.call_args.kwargs
            loop_runner_kwargs = call_kwargs.get("loop_runner_kwargs")
            assert loop_runner_kwargs is not None
            assert loop_runner_kwargs.get("tools") == [mock_tool]

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__passes_all_kwargs__to_handler(
        self,
        mock_stream: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify all kwargs are passed through to the handler.
        Why this matters: Optional kwargs should not be lost.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=5)
        runner = BasicLoopIterationRunner(config=config)
        mock_stream.return_value = create_stream_response()
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )
        mock_tool = create_mock_tool()

        # Act
        await runner(
            iteration_index=1,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tools=[mock_tool],
            start_text="Starting response...",
            temperature=0.7,
            debug_info={"key": "value"},
        )

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        loop_runner_kwargs = call_kwargs.get("loop_runner_kwargs")
        assert loop_runner_kwargs is not None
        assert loop_runner_kwargs.get("start_text") == "Starting response..."
        assert loop_runner_kwargs.get("temperature") == 0.7
        assert loop_runner_kwargs.get("debug_info") == {"key": "value"}

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_call__returns_response_from_handler(
        self,
        mock_stream: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify the runner returns the response from the handler.
        Why this matters: Response should be passed through unchanged.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=5)
        runner = BasicLoopIterationRunner(config=config)

        expected_response = create_stream_response(
            text="Custom response text",
            tool_calls=[LanguageModelFunction(id="tc_1", name="Tool", arguments={})],
        )
        mock_stream.return_value = expected_response

        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )

        # Act
        result = await runner(
            iteration_index=1,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        assert result == expected_response
        assert result.message.text == "Custom response text"
        assert result.tool_calls is not None
        assert result.tool_calls[0].name == "Tool"


# Integration-style tests for routing logic
class TestBasicLoopIterationRunnerRouting:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_last_iteration",
        new_callable=AsyncMock,
    )
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_routing__calls_forced_tools__when_conditions_met(
        self,
        mock_normal: AsyncMock,
        mock_last: AsyncMock,
        mock_forced: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify forced tools handler is called when conditions are met.
        Why this matters: Routing logic correctness is critical.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=5)
        runner = BasicLoopIterationRunner(config=config)
        mock_forced.return_value = create_stream_response()

        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool"}}
        ]

        # Act
        await runner(
            iteration_index=0,
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
        )

        # Assert
        mock_forced.assert_called_once()
        mock_last.assert_not_called()
        mock_normal.assert_not_called()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_last_iteration",
        new_callable=AsyncMock,
    )
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_routing__calls_last_iteration__when_at_max(
        self,
        mock_normal: AsyncMock,
        mock_last: AsyncMock,
        mock_forced: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify last iteration handler is called at max iterations.
        Why this matters: Routing logic correctness is critical.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=5)
        runner = BasicLoopIterationRunner(config=config)
        mock_last.return_value = create_stream_response()

        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )

        # Act
        await runner(
            iteration_index=4,  # max - 1
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        mock_forced.assert_not_called()
        mock_last.assert_called_once()
        mock_normal.assert_not_called()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_last_iteration",
        new_callable=AsyncMock,
    )
    @patch(
        "unique_toolkit.agentic.loop_runner.runners.basic.handle_normal_iteration",
        new_callable=AsyncMock,
    )
    async def test_routing__calls_normal_iteration__for_middle_iterations(
        self,
        mock_normal: AsyncMock,
        mock_last: AsyncMock,
        mock_forced: AsyncMock,
        mock_streaming_handler: MagicMock,
        mock_language_model: LanguageModelInfo,
    ) -> None:
        """
        Purpose: Verify normal iteration handler is called for middle iterations.
        Why this matters: Routing logic correctness is critical.
        """
        # Arrange
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=5)
        runner = BasicLoopIterationRunner(config=config)
        mock_normal.return_value = create_stream_response()

        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="Hello")]
        )

        # Act
        await runner(
            iteration_index=2,  # Middle iteration
            messages=messages,
            model=mock_language_model,
            streaming_handler=mock_streaming_handler,
        )

        # Assert
        mock_forced.assert_not_called()
        mock_last.assert_not_called()
        mock_normal.assert_called_once()
