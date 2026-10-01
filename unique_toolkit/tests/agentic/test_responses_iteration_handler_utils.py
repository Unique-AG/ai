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
    LanguageModelToolDescription,
    ResponsesLanguageModelStreamResponse,
)

CODE_INTERPRETER_TOOL = {"type": "code_interpreter", "container": {"type": "auto"}}


def _function_tool(name: str) -> LanguageModelToolDescription:
    return LanguageModelToolDescription(
        name=name, description=f"{name} description", parameters={}
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


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_handle_responses_forced_tools_iteration__drops_code_interpreter__when_function_is_forced(
    mock_stream: AsyncMock,
    base_kwargs: _ResponsesLoopIterationRunnerKwargs,
) -> None:
    """
    Purpose: A forced function request must not carry the hosted
    ``code_interpreter`` tool.
    Why this matters: GPT-5.6 Sol returns HTTP 400 "Tool choices other than
    'auto' are not supported ... 'code_interpreter'" when a named tool_choice
    is sent next to a hosted tool (UN-26836). Code Interpreter is a capability
    tool, so the tool manager keeps it in ``tools`` even when another tool is
    forced.
    Setup summary: tools = [UploadedSearch, code_interpreter], one forced
    function choice; assert the request tools contain only the function.
    """
    mock_stream.return_value = _make_response()
    uploaded_search = _function_tool("UploadedSearch")
    base_kwargs["tools"] = [uploaded_search, CODE_INTERPRETER_TOOL]  # type: ignore[list-item]
    base_kwargs["tool_choices"] = [{"type": "function", "name": "UploadedSearch"}]

    await handle_responses_forced_tools_iteration(**base_kwargs)

    call_kwargs = mock_stream.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "function", "name": "UploadedSearch"}
    assert call_kwargs["tools"] == [uploaded_search]


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_handle_responses_forced_tools_iteration__keeps_other_functions__when_function_is_forced(
    mock_stream: AsyncMock,
    base_kwargs: _ResponsesLoopIterationRunnerKwargs,
) -> None:
    """
    Purpose: Only hosted tools are dropped; other function tools stay.
    Why this matters: Function tools such as Ask User are also capability
    tools, but the API accepts them next to a named tool_choice. Removing
    every capability tool would be wider than the API constraint.
    Setup summary: tools = [two functions, code_interpreter]; assert both
    functions remain and the hosted tool is gone.
    """
    mock_stream.return_value = _make_response()
    forced = _function_tool("UploadedSearch")
    ask_user = _function_tool("AskUser")
    base_kwargs["tools"] = [forced, CODE_INTERPRETER_TOOL, ask_user]  # type: ignore[list-item]
    base_kwargs["tool_choices"] = [{"type": "function", "name": "UploadedSearch"}]

    await handle_responses_forced_tools_iteration(**base_kwargs)

    assert mock_stream.call_args.kwargs["tools"] == [forced, ask_user]


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_handle_responses_forced_tools_iteration__keeps_code_interpreter__when_it_is_forced(
    mock_stream: AsyncMock,
    base_kwargs: _ResponsesLoopIterationRunnerKwargs,
) -> None:
    """
    Purpose: Forcing the code interpreter itself must keep it in ``tools``.
    Why this matters: The filter only applies to a forced *function*. A
    hosted tool_choice (``{"type": "code_interpreter"}``) needs its tool.
    Setup summary: tools = [function, code_interpreter], forced choice is the
    hosted type; assert the tool list is passed through unchanged.
    """
    mock_stream.return_value = _make_response()
    tools = [_function_tool("UploadedSearch"), CODE_INTERPRETER_TOOL]
    base_kwargs["tools"] = tools  # type: ignore[typeddict-item]
    base_kwargs["tool_choices"] = [{"type": "code_interpreter"}]  # type: ignore[list-item]

    await handle_responses_forced_tools_iteration(**base_kwargs)

    assert mock_stream.call_args.kwargs["tools"] == tools


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.loop_runner._responses_iteration_handler_utils.responses_stream_response",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_handle_responses_forced_tools_iteration__omits_tools_kwarg__when_no_tools_given(
    mock_stream: AsyncMock,
    base_kwargs: _ResponsesLoopIterationRunnerKwargs,
) -> None:
    """
    Purpose: Without a ``tools`` entry the request shape is unchanged.
    Why this matters: Callers that never set ``tools`` must not suddenly get
    ``tools=None`` injected into the streaming handler call.
    Setup summary: delete ``tools`` from kwargs; assert the stream call has no
    ``tools`` keyword.
    """
    mock_stream.return_value = _make_response()
    del base_kwargs["tools"]
    base_kwargs["tool_choices"] = [{"type": "function", "name": "Tool1"}]

    await handle_responses_forced_tools_iteration(**base_kwargs)

    assert "tools" not in mock_stream.call_args.kwargs
