"""
Tests for _iteration_handler_utils module.

This file contains tests for the iteration handler utility functions
that manage different types of loop iterations (normal, last, forced tools).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.chat import ChatCompletionNamedToolChoiceParam

from unique_toolkit.agentic.loop_runner._iteration_handler_utils import (
    handle_forced_tools_iteration,
    handle_last_iteration,
    handle_normal_iteration,
    run_forced_tools_iteration,
)
from unique_toolkit.agentic.loop_runner.base import _LoopIterationRunnerKwargs
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
def mock_language_model() -> LanguageModelInfo:
    """Provide a language model info for tests."""
    return LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0513)


@pytest.fixture
def base_kwargs(
    mock_streaming_handler: MagicMock,
    mock_language_model: LanguageModelInfo,
) -> _LoopIterationRunnerKwargs:
    """Provide base kwargs for iteration handlers."""
    messages = LanguageModelMessages(
        root=[LanguageModelUserMessage(content="Hello")]
    )
    return _LoopIterationRunnerKwargs(
        iteration_index=0,
        streaming_handler=mock_streaming_handler,
        messages=messages,
        model=mock_language_model,
    )


# Tests for handle_last_iteration
class TestHandleLastIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_handle_last_iteration__calls_stream_response__with_tools_none(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify handle_last_iteration removes tools.
        Why this matters: Last iteration should force text response without tools.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        # Act
        result = await handle_last_iteration(**base_kwargs)

        # Assert
        assert result is not None
        mock_stream.assert_called_once()
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") is None

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_handle_last_iteration__returns_stream_response__correctly(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify handle_last_iteration returns the stream response.
        Why this matters: Response should be passed through correctly.
        """
        # Arrange
        expected_response = create_stream_response(text="Final answer")
        mock_stream.return_value = expected_response

        # Act
        result = await handle_last_iteration(**base_kwargs)

        # Assert
        assert result == expected_response
        assert result.message.text == "Final answer"


# Tests for handle_normal_iteration
class TestHandleNormalIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_handle_normal_iteration__calls_stream_response__with_kwargs(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify handle_normal_iteration calls stream_response.
        Why this matters: Normal iteration should pass kwargs through.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        # Act
        result = await handle_normal_iteration(**base_kwargs)

        # Assert
        assert result is not None
        mock_stream.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_handle_normal_iteration__preserves_tools__in_kwargs(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify handle_normal_iteration preserves tools in kwargs.
        Why this matters: Normal iteration should not modify tools.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()
        mock_tool = create_mock_tool()
        base_kwargs["tools"] = [mock_tool]

        # Act
        await handle_normal_iteration(**base_kwargs)

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        loop_runner_kwargs = call_kwargs.get("loop_runner_kwargs")
        assert loop_runner_kwargs is not None
        assert loop_runner_kwargs.get("tools") == [mock_tool]


# Tests for handle_forced_tools_iteration
class TestHandleForcedToolsIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.run_forced_tools_iteration",
        new_callable=AsyncMock,
    )
    async def test_handle_forced_tools_iteration__delegates__to_run_forced_tools_iteration(
        self,
        mock_run_forced: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify handle_forced_tools_iteration delegates to run_forced_tools_iteration.
        Why this matters: Function should correctly delegate work.
        """
        # Arrange
        expected_response = create_stream_response()
        mock_run_forced.return_value = expected_response
        base_kwargs["tool_choices"] = [
            {"type": "function", "function": {"name": "TestTool"}}
        ]

        # Act
        result = await handle_forced_tools_iteration(**base_kwargs)

        # Assert
        assert result == expected_response
        mock_run_forced.assert_called_once()


# Tests for run_forced_tools_iteration
class TestRunForcedToolsIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__merges_tool_calls__from_multiple_responses(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify tool calls are merged from multiple forced tool responses.
        Why this matters: Multiple forced tools should produce combined result.
        """
        # Arrange
        tool_call_1 = LanguageModelFunction(
            id="call_1", name="Tool1", arguments={}
        )
        tool_call_2 = LanguageModelFunction(
            id="call_2", name="Tool2", arguments={}
        )

        mock_stream.side_effect = [
            create_stream_response(tool_calls=[tool_call_1]),
            create_stream_response(tool_calls=[tool_call_2]),
        ]

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("Tool1"), create_mock_tool("Tool2")]

        # Act
        result = await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].name == "Tool1"
        assert result.tool_calls[1].name == "Tool2"

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__merges_references__from_multiple_responses(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
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
            url="https://example.com/1",
        )
        ref_2 = ContentReference(
            id="ref_2",
            name="ref_2",
            sequence_number=2,
            source="Source 2",
            source_id="src_2",
            url="https://example.com/2",
        )

        mock_stream.side_effect = [
            create_stream_response(references=[ref_1]),
            create_stream_response(references=[ref_2]),
        ]

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("Tool1"), create_mock_tool("Tool2")]

        # Act
        result = await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        assert len(result.message.references) == 2
        assert result.message.references[0].id == "ref_1"
        assert result.message.references[1].id == "ref_2"

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__limits_tools__to_matching_tool(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify each tool choice only sends the matching tool.
        Why this matters: Limiting tools prevents model from calling wrong tool.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]
        mock_search_tool = create_mock_tool("SearchTool")
        mock_other_tool = create_mock_tool("OtherTool")

        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [mock_search_tool, mock_other_tool]

        # Act
        await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") == [mock_search_tool]

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__handles_missing_tool__gracefully(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify graceful handling when requested tool is not in available tools.
        Why this matters: Should not fail when tool_choice refers to unknown tool.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "UnknownTool"}}
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("KnownTool")]

        # Act
        await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") is None

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__returns_none_tool_calls__when_no_tools_called(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify tool_calls is None when no tool calls in responses.
        Why this matters: Empty tool calls should be represented as None.
        """
        # Arrange
        mock_stream.return_value = create_stream_response(tool_calls=None)

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}}
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("Tool1")]

        # Act
        result = await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        assert result.tool_calls is None

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__calls_prepare_kwargs__when_provided(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify prepare_loop_runner_kwargs is called for each tool choice.
        Why this matters: Custom message rewriting should be supported (e.g., for Qwen).
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("Tool1"), create_mock_tool("Tool2")]

        prepare_kwargs = MagicMock()
        prepare_kwargs.side_effect = lambda func_name, kwargs: kwargs

        # Act
        await run_forced_tools_iteration(
            loop_runner_kwargs=base_kwargs,
            prepare_loop_runner_kwargs=prepare_kwargs,
        )

        # Assert
        assert prepare_kwargs.call_count == 2
        prepare_kwargs.assert_any_call("Tool1", base_kwargs)

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__uses_prepared_kwargs__in_stream_response(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify prepared kwargs are used when calling stream_response.
        Why this matters: Custom modifications should be applied to API calls.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}}
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("Tool1")]

        modified_kwargs = dict(base_kwargs)
        modified_kwargs["start_text"] = "Modified start text"

        def prepare_kwargs(
            func_name: str | None,
            per_choice_kwargs: _LoopIterationRunnerKwargs,
        ) -> _LoopIterationRunnerKwargs:
            result = _LoopIterationRunnerKwargs(**per_choice_kwargs)
            result["start_text"] = "Modified start text"
            return result

        # Act
        await run_forced_tools_iteration(
            loop_runner_kwargs=base_kwargs,
            prepare_loop_runner_kwargs=prepare_kwargs,
        )

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs["loop_runner_kwargs"].get("start_text") == "Modified start text"

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__passes_tool_choice__to_stream_response(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify tool_choice is passed to stream_response.
        Why this matters: API needs the tool_choice to force specific tool.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        tool_choice: ChatCompletionNamedToolChoiceParam = {
            "type": "function",
            "function": {"name": "SearchTool"},
        }
        base_kwargs["tool_choices"] = [tool_choice]
        base_kwargs["tools"] = [create_mock_tool("SearchTool")]

        # Act
        await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tool_choice") == tool_choice

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__handles_no_tools_list__gracefully(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify handling when tools list is not provided.
        Why this matters: Should handle missing tools list without error.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}}
        ]
        base_kwargs["tool_choices"] = tool_choices
        # Note: not setting base_kwargs["tools"]

        # Act
        await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert - should not raise and should not pass tools
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") is None

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__handles_tool_choice_without_function_name(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify handling when tool_choice has no function name.
        Why this matters: Should handle malformed tool_choice gracefully.
        """
        # Arrange
        mock_stream.return_value = create_stream_response()

        # Malformed tool_choice without function name
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {}}  # type: ignore[typeddict-item]
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("Tool1")]

        # Act - should not raise
        await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") is None

    @pytest.mark.ai
    async def test_run_forced_tools_iteration__raises__when_no_tool_choices(
        self,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify assertion error when tool_choices is empty.
        Why this matters: Function requires at least one tool choice.
        """
        # Arrange
        base_kwargs["tool_choices"] = []

        # Act & Assert
        with pytest.raises(AssertionError, match="at least one tool choice"):
            await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__returns_first_response_base__for_merged_result(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify the base response comes from the first stream response.
        Why this matters: Message text and id should come from first response.
        """
        # Arrange
        response_1 = create_stream_response(text="First response")
        response_2 = create_stream_response(text="Second response")
        mock_stream.side_effect = [response_1, response_2]

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("Tool1"), create_mock_tool("Tool2")]

        # Act
        result = await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        assert result.message.text == "First response"

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_run_forced_tools_iteration__handles_single_tool_choice(
        self,
        mock_stream: AsyncMock,
        base_kwargs: _LoopIterationRunnerKwargs,
    ) -> None:
        """
        Purpose: Verify correct behavior with a single tool choice.
        Why this matters: Single tool case should work without special handling.
        """
        # Arrange
        tool_call = LanguageModelFunction(id="call_1", name="Tool1", arguments={})
        mock_stream.return_value = create_stream_response(tool_calls=[tool_call])

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}}
        ]
        base_kwargs["tool_choices"] = tool_choices
        base_kwargs["tools"] = [create_mock_tool("Tool1")]

        # Act
        result = await run_forced_tools_iteration(loop_runner_kwargs=base_kwargs)

        # Assert
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "Tool1"
        mock_stream.assert_called_once()
