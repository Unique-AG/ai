"""Tests for ResponsesStreamingHandler include injection (UN-17972).

The handler always requests code_interpreter_call.outputs so UniqueAI stays
generic (no isinstance checks) and code interpreter execution logs attach to
tool calls whenever code interpreter runs.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_orchestrator.unique_ai_builder import (
    ResponsesStreamingHandler,
    _ChatServiceResponsesStreaming,
)


def _make_handler() -> ResponsesStreamingHandler:
    inner = MagicMock()
    inner.complete_with_references_async = AsyncMock(return_value=MagicMock())
    inner.complete_with_references = MagicMock(return_value=MagicMock())
    return ResponsesStreamingHandler(inner=inner)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_responses_streaming_handler__always_injects_include__async_path() -> (
    None
):
    """complete_with_references_async always sets include=code_interpreter_call.outputs."""
    handler = _make_handler()

    await handler.complete_with_references_async(messages=[], model_name="model")

    call_kwargs = handler._inner.complete_with_references_async.await_args.kwargs
    assert call_kwargs["include"] == ["code_interpreter_call.outputs"]


@pytest.mark.ai
def test_responses_streaming_handler__always_injects_include__sync_path() -> None:
    """The synchronous complete_with_references also always sets include."""
    handler = _make_handler()

    handler.complete_with_references(messages=[], model_name="model")

    call_kwargs = handler._inner.complete_with_references.call_args.kwargs
    assert call_kwargs["include"] == ["code_interpreter_call.outputs"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_chat_service_responses_streaming__forwards_to_responses_methods() -> (
    None
):
    """
    Purpose: The legacy adapter must route the protocol's
    `complete_with_references[_async]` to ChatService's Responses-specific
    methods, not the Chat Completions ones.
    Why this matters: ChatService exposes both; routing to the wrong method
    would silently stream through the Chat Completions API.
    """
    chat_service = MagicMock()
    chat_service.complete_responses_with_references = MagicMock(
        return_value=MagicMock()
    )
    chat_service.complete_responses_with_references_async = AsyncMock(
        return_value=MagicMock()
    )
    adapter = _ChatServiceResponsesStreaming(chat_service)

    adapter.complete_with_references(messages=[], model_name="model")
    await adapter.complete_with_references_async(messages=[], model_name="model")

    chat_service.complete_responses_with_references.assert_called_once()
    chat_service.complete_responses_with_references_async.assert_awaited_once()
    chat_service.complete_with_references.assert_not_called()
