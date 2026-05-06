"""Tests for ResponsesStreamingHandler include injection (UN-17972).

The include forwarding logic lives in ResponsesStreamingHandler in
unique_ai_builder.py so that UniqueAI stays generic (no isinstance checks).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.agentic.tools.tool_manager import ResponsesApiToolManager

from unique_orchestrator.unique_ai_builder import ResponsesStreamingHandler


def _make_handler(
    include_params: list[str],
) -> ResponsesStreamingHandler:
    tool_manager = MagicMock(spec=ResponsesApiToolManager)
    tool_manager.get_required_include_params.return_value = include_params
    chat_service = MagicMock()
    chat_service.complete_responses_with_references_async = AsyncMock(
        return_value=MagicMock()
    )
    chat_service.complete_responses_with_references = MagicMock(
        return_value=MagicMock()
    )
    return ResponsesStreamingHandler(
        chat_service=chat_service,
        tool_manager=tool_manager,
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_responses_streaming_handler__injects_include__when_tool_manager_returns_params() -> (
    None
):
    """
    Purpose: Verify complete_with_references_async injects include when the tool
    manager returns a non-empty list.
    Why this matters: UN-17972 requires code_interpreter_call.outputs on the
    Responses API so execution logs attach to tool calls.
    """
    handler = _make_handler(include_params=["code_interpreter_call.outputs"])

    await handler.complete_with_references_async(messages=[], model_name="model")

    call_kwargs = (
        handler._chat_service.complete_responses_with_references_async.await_args.kwargs
    )
    assert call_kwargs["include"] == ["code_interpreter_call.outputs"]
    handler._tool_manager.get_required_include_params.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_responses_streaming_handler__omits_include__when_tool_manager_returns_empty() -> (
    None
):
    """
    Purpose: Verify include is not added when get_required_include_params returns [].
    Why this matters: No extra include should reach the Responses API when no tool
    requests it — preserving legacy behaviour exactly.
    """
    handler = _make_handler(include_params=[])

    await handler.complete_with_references_async(messages=[], model_name="model")

    call_kwargs = (
        handler._chat_service.complete_responses_with_references_async.await_args.kwargs
    )
    assert "include" not in call_kwargs


@pytest.mark.ai
def test_responses_streaming_handler__injects_include__sync_path() -> None:
    """
    Purpose: Verify the synchronous complete_with_references also injects include.
    """
    handler = _make_handler(include_params=["code_interpreter_call.outputs"])

    handler.complete_with_references(messages=[], model_name="model")

    call_kwargs = (
        handler._chat_service.complete_responses_with_references.call_args.kwargs
    )
    assert call_kwargs["include"] == ["code_interpreter_call.outputs"]


@pytest.mark.ai
def test_responses_streaming_handler__omits_include__sync_path_when_empty() -> None:
    """Purpose: No include injected via sync path when tool manager returns []."""
    handler = _make_handler(include_params=[])

    handler.complete_with_references(messages=[], model_name="model")

    call_kwargs = (
        handler._chat_service.complete_responses_with_references.call_args.kwargs
    )
    assert "include" not in call_kwargs
