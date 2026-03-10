"""
Tests for MistralLoopIterationRunner.

Verifies that the Mistral runner overrides forced tool handling to use
tool_choice_override="any" while inheriting all other behavior from
BasicLoopIterationRunner.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.chat import ChatCompletionNamedToolChoiceParam

from unique_toolkit.agentic.loop_runner.runners.basic import (
    BasicLoopIterationRunnerConfig,
)
from unique_toolkit.agentic.loop_runner.runners.mistral import (
    MistralLoopIterationRunner,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelUserMessage,
)


def create_stream_response(
    text: str = "Response text",
    tool_calls: list[LanguageModelFunction] | None = None,
    references: list[ContentReference] | None = None,
) -> LanguageModelStreamResponse:
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
    tool = MagicMock()
    tool.name = name
    return tool


@pytest.fixture
def runner() -> MistralLoopIterationRunner:
    return MistralLoopIterationRunner(
        config=BasicLoopIterationRunnerConfig(max_loop_iterations=5),
    )


@pytest.fixture
def mock_streaming_handler() -> MagicMock:
    handler = MagicMock()
    handler.complete_with_references_async = AsyncMock()
    return handler


class TestMistralLoopIterationRunnerInit:
    @pytest.mark.ai
    def test_runner__is_subclass_of_basic(self) -> None:
        from unique_toolkit.agentic.loop_runner.runners.basic import (
            BasicLoopIterationRunner,
        )

        runner = MistralLoopIterationRunner(
            config=BasicLoopIterationRunnerConfig(max_loop_iterations=5),
        )
        assert isinstance(runner, BasicLoopIterationRunner)

    @pytest.mark.ai
    def test_runner__stores_config(self) -> None:
        config = BasicLoopIterationRunnerConfig(max_loop_iterations=7)
        runner = MistralLoopIterationRunner(config=config)
        assert runner._config.max_loop_iterations == 7


class TestMistralForcedToolsIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__uses_any_tool_choice__for_single_tool(
        self,
        mock_stream: AsyncMock,
        runner: MistralLoopIterationRunner,
        mock_streaming_handler: MagicMock,
    ) -> None:
        mock_stream.return_value = create_stream_response()

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]

        await runner(
            iteration_index=0,
            messages=LanguageModelMessages(
                root=[LanguageModelUserMessage(content="Hello")]
            ),
            model="mistral-large-latest",
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[create_mock_tool("SearchTool")],
        )

        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tool_choice") == "any"

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__uses_any_for_every_tool__with_multiple_tools(
        self,
        mock_stream: AsyncMock,
        runner: MistralLoopIterationRunner,
        mock_streaming_handler: MagicMock,
    ) -> None:
        mock_stream.return_value = create_stream_response()

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]

        await runner(
            iteration_index=0,
            messages=LanguageModelMessages(
                root=[LanguageModelUserMessage(content="Hello")]
            ),
            model="mistral-large-latest",
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[create_mock_tool("Tool1"), create_mock_tool("Tool2")],
        )

        assert mock_stream.call_count == 2
        for call in mock_stream.call_args_list:
            assert call.kwargs.get("tool_choice") == "any"

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__merges_tool_calls__from_multiple_responses(
        self,
        mock_stream: AsyncMock,
        runner: MistralLoopIterationRunner,
        mock_streaming_handler: MagicMock,
    ) -> None:
        tool_call_1 = LanguageModelFunction(id="c1", name="Tool1", arguments={})
        tool_call_2 = LanguageModelFunction(id="c2", name="Tool2", arguments={})

        mock_stream.side_effect = [
            create_stream_response(tool_calls=[tool_call_1]),
            create_stream_response(tool_calls=[tool_call_2]),
        ]

        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]

        result = await runner(
            iteration_index=0,
            messages=LanguageModelMessages(
                root=[LanguageModelUserMessage(content="Hello")]
            ),
            model="mistral-large-latest",
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[create_mock_tool("Tool1"), create_mock_tool("Tool2")],
        )

        assert result.tool_calls is not None
        assert len(result.tool_calls) == 2


class TestMistralInheritedBehavior:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_normal_iteration__delegates_to_basic(
        self,
        mock_stream: AsyncMock,
        runner: MistralLoopIterationRunner,
        mock_streaming_handler: MagicMock,
    ) -> None:
        mock_stream.return_value = create_stream_response()

        result = await runner(
            iteration_index=1,
            messages=LanguageModelMessages(
                root=[LanguageModelUserMessage(content="Hello")]
            ),
            model="mistral-large-latest",
            streaming_handler=mock_streaming_handler,
        )

        assert result is not None
        mock_stream.assert_called_once()

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_last_iteration__removes_tools(
        self,
        mock_stream: AsyncMock,
        runner: MistralLoopIterationRunner,
        mock_streaming_handler: MagicMock,
    ) -> None:
        mock_stream.return_value = create_stream_response()

        result = await runner(
            iteration_index=4,
            messages=LanguageModelMessages(
                root=[LanguageModelUserMessage(content="Hello")]
            ),
            model="mistral-large-latest",
            streaming_handler=mock_streaming_handler,
        )

        assert result is not None
        call_kwargs = mock_stream.call_args.kwargs
        assert call_kwargs.get("tools") is None
