"""Tests for _responses_iteration_handler_utils module — specifically the
usage-summing fix for handle_responses_forced_tools_iteration (mirrors the
Chat Completions forced-tools usage merge in _iteration_handler_utils.py)."""

from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils import (
    handle_responses_forced_tools_iteration,
)
from unique_toolkit.agentic.loop_runner.base import (
    _ResponsesLoopIterationRunnerKwargs,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelStreamResponseMessage,
    LanguageModelTokenUsage,
    ResponsesLanguageModelStreamResponse,
)


def _make_message() -> LanguageModelStreamResponseMessage:
    return LanguageModelStreamResponseMessage(
        id="msg-1",
        chat_id="chat-1",
        previous_message_id=None,
        role=LanguageModelMessageRole.ASSISTANT,
        text="hello",
    )


def _make_response(
    usage: LanguageModelTokenUsage | None = None,
) -> ResponsesLanguageModelStreamResponse:
    return ResponsesLanguageModelStreamResponse(
        message=_make_message(),
        output=[],
        usage=usage,
    )


@pytest.fixture
def base_kwargs() -> _ResponsesLoopIterationRunnerKwargs:
    return {
        "messages": None,  # type: ignore[typeddict-item]
        "iteration_index": 0,
        "streaming_handler": None,  # type: ignore[typeddict-item]
        "model": None,  # type: ignore[typeddict-item]
        "tools": [],
        "content_chunks": [],
        "start_text": None,
        "debug_info": {},
        "temperature": 0.0,
        "tool_choices": [
            {"type": "function", "function": {"name": "Tool1"}},
            {"type": "function", "function": {"name": "Tool2"}},
        ],
        "other_options": None,
    }


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_handle_responses_forced_tools_iteration__sums_usage__from_multiple_responses(
    mock_stream: AsyncMock,
    base_kwargs: _ResponsesLoopIterationRunnerKwargs,
) -> None:
    """
    Purpose: Verify token usage is summed across all forced-tool-choice calls
    in the Responses API path, matching the Chat Completions fix.
    Why this matters: each tool choice is a separate, real, billable LLM call
    — dropping all but the first response's usage would silently undercount
    token spend for any iteration with 2+ forced tools.
    """
    mock_stream.side_effect = [
        _make_response(
            usage=LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            )
        ),
        _make_response(
            usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            )
        ),
    ]

    result = await handle_responses_forced_tools_iteration(**base_kwargs)

    assert result.usage == LanguageModelTokenUsage(
        completion_tokens=11,
        prompt_tokens=22,
        total_tokens=33,
    )


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_handle_responses_forced_tools_iteration__usage_none_on_all__returns_none(
    mock_stream: AsyncMock,
    base_kwargs: _ResponsesLoopIterationRunnerKwargs,
) -> None:
    """When no response carries usage, the merged result must be None, not a
    zeroed-out usage object implying zero tokens were spent."""
    mock_stream.side_effect = [_make_response(), _make_response()]

    result = await handle_responses_forced_tools_iteration(**base_kwargs)

    assert result.usage is None
