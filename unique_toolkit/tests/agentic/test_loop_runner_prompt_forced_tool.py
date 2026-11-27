"""
Tests for PromptForcedToolLoopIterationRunner.

Verifies that forced-tool iterations send tool_choice "auto" and ask for the
named tool in the prompt, because Opus 5.5 and Fable 5.1 reject named and
"any" tool choices.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.chat import ChatCompletionNamedToolChoiceParam

from unique_toolkit.agentic.loop_runner.runners.basic import (
    BasicLoopIterationRunner,
    BasicLoopIterationRunnerConfig,
)
from unique_toolkit.agentic.loop_runner.runners.prompt_forced_tool import (
    PromptForcedToolLoopIterationRunner,
)
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelUserMessage,
)


def create_stream_response(text: str = "Response text") -> LanguageModelStreamResponse:
    return LanguageModelStreamResponse(
        message=ChatMessage(
            id="msg_123",
            chat_id="",
            previous_message_id="prev_msg_123",
            role=LanguageModelMessageRole.ASSISTANT,
            text=text,
            original_text=text,
            references=[],
        ),
        tool_calls=None,
    )


def create_mock_tool(name: str) -> MagicMock:
    tool = MagicMock()
    tool.name = name
    return tool


def _user_messages(content: str = "Hello") -> LanguageModelMessages:
    return LanguageModelMessages(root=[LanguageModelUserMessage(content=content)])


OPUS_5_5 = LanguageModelInfo.from_name(LanguageModelName.ANTHROPIC_CLAUDE_OPUS_5_5)


@pytest.fixture
def runner() -> PromptForcedToolLoopIterationRunner:
    return PromptForcedToolLoopIterationRunner(
        config=BasicLoopIterationRunnerConfig(max_loop_iterations=5),
    )


@pytest.fixture
def mock_streaming_handler() -> MagicMock:
    handler = MagicMock()
    handler.complete_with_references_async = AsyncMock()
    return handler


class TestPromptForcedToolLoopIterationRunnerInit:
    @pytest.mark.ai
    def test_runner__is_subclass_of_basic(self) -> None:
        """
        Purpose: Verify the runner inherits the basic iteration routing.
        Why this matters: Later iterations must keep the shared loop behavior.
        Setup summary: Construct the runner and check its type.
        """
        runner = PromptForcedToolLoopIterationRunner(
            config=BasicLoopIterationRunnerConfig(max_loop_iterations=5),
        )
        assert isinstance(runner, BasicLoopIterationRunner)


class TestPromptForcedToolIteration:
    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__sends_auto_and_names_tool__for_single_tool(
        self,
        mock_stream: AsyncMock,
        runner: PromptForcedToolLoopIterationRunner,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify a forced tool is requested with tool_choice auto and a prompt.
        Why this matters: Named tool_choice returns HTTP 400 on Opus 5.5.
        Setup summary: Force SearchTool and inspect the streamed request.
        """
        mock_stream.return_value = create_stream_response()
        messages = _user_messages()
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]

        await runner(
            iteration_index=0,
            messages=messages,
            model=OPUS_5_5,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[create_mock_tool("SearchTool")],
        )

        call_kwargs = mock_stream.call_args.kwargs
        streamed_content = call_kwargs["loop_runner_kwargs"]["messages"].root[0].content
        assert call_kwargs.get("tool_choice") == "auto"
        assert [tool.name for tool in call_kwargs["tools"]] == ["SearchTool"]
        assert "You must call the tool SearchTool." in streamed_content
        assert messages.root[0].content == "Hello"

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_forced_tools__names_each_tool__with_multiple_tools(
        self,
        mock_stream: AsyncMock,
        runner: PromptForcedToolLoopIterationRunner,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify each forced tool gets its own auto request and prompt.
        Why this matters: Multiple tool_choices must still each be requested.
        Setup summary: Force Tool1 and Tool2 and inspect both streamed requests.
        """
        mock_stream.return_value = create_stream_response()
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ]

        await runner(
            iteration_index=0,
            messages=_user_messages(),
            model=OPUS_5_5,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[create_mock_tool("Tool1"), create_mock_tool("Tool2")],
        )

        assert mock_stream.call_count == 2
        first = mock_stream.call_args_list[0].kwargs
        second = mock_stream.call_args_list[1].kwargs
        assert first.get("tool_choice") == "auto"
        assert second.get("tool_choice") == "auto"
        assert [tool.name for tool in first["tools"]] == ["Tool1"]
        assert [tool.name for tool in second["tools"]] == ["Tool2"]
        assert (
            "You must call the tool Tool1."
            in first["loop_runner_kwargs"]["messages"].root[0].content
        )
        assert (
            "You must call the tool Tool2."
            in second["loop_runner_kwargs"]["messages"].root[0].content
        )

    @pytest.mark.ai
    @patch(
        "unique_toolkit.agentic.loop_runner._iteration_handler_utils.stream_response",
        new_callable=AsyncMock,
    )
    async def test_later_iteration__leaves_user_message_unchanged(
        self,
        mock_stream: AsyncMock,
        runner: PromptForcedToolLoopIterationRunner,
        mock_streaming_handler: MagicMock,
    ) -> None:
        """
        Purpose: Verify iterations after the first do not append the must-call prompt.
        Why this matters: Only the opening forced-tool turn needs the workaround.
        Setup summary: Run iteration 1 with tool choices present and inspect the message.
        """
        mock_stream.return_value = create_stream_response()
        tool_choices: list[ChatCompletionNamedToolChoiceParam] = [
            {"type": "function", "function": {"name": "SearchTool"}}
        ]

        await runner(
            iteration_index=1,
            messages=_user_messages(),
            model=OPUS_5_5,
            streaming_handler=mock_streaming_handler,
            tool_choices=tool_choices,
            tools=[create_mock_tool("SearchTool")],
        )

        streamed_content = (
            mock_stream.call_args.kwargs["loop_runner_kwargs"]["messages"]
            .root[0]
            .content
        )
        assert streamed_content == "Hello"
        assert "tool_choice" not in mock_stream.call_args.kwargs
