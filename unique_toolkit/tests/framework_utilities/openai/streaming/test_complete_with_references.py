"""Tests for orchestrator-level behavior of the streaming
``ChatCompletionsCompleteWithReferences`` and ``ResponsesCompleteWithReferences``.

Focused on the invariants that handlers/routers/subscribers cannot observe on
their own: per-request context cleanup, re-entry guards, and graceful handling
of subscriber/SDK failures at orchestrator boundaries.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueApi,
    UniqueApp,
    UniqueContext,
    UniqueSettings,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.complete_with_references import (
    ChatCompletionsCompleteWithReferences,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.events import (
    StreamStarted,
)


def _settings_with_chat() -> UniqueSettings:
    auth = AuthContext(user_id=SecretStr("user-1"), company_id=SecretStr("company-1"))
    chat = ChatContext(
        chat_id="chat-1",
        assistant_id="assistant-1",
        last_assistant_message_id="amsg-1",
        last_user_message_id="umsg-1",
        last_user_message_text="",
    )
    s = UniqueSettings(auth=auth, app=UniqueApp(), api=UniqueApi())
    s._context = UniqueContext(auth=auth, chat=chat)
    return s


class _FakeStream:
    """Async iterable stand-in for the OpenAI streaming response object."""

    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = chunks

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk


def _build_orchestrator(
    *,
    client: Any,
) -> ChatCompletionsCompleteWithReferences:
    """Build an orchestrator with no default subscribers and an injected client."""
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.stream_event_router import (
        ChatCompletionStreamEventRouter,
    )
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.text_handler import (
        ChatCompletionTextHandler,
    )
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.tool_call_handler import (
        ChatCompletionToolCallHandler,
    )

    router = ChatCompletionStreamEventRouter(
        text_handler=ChatCompletionTextHandler(replacers=[]),
        tool_call_handler=ChatCompletionToolCallHandler(),
    )
    return ChatCompletionsCompleteWithReferences(
        _settings_with_chat(),
        client=client,
        router=router,
        subscribers=(),
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completions__stream_started_subscriber_raises__clears_context():
    """
    Purpose: When a ``stream_started`` subscriber raises, per-request context
      must still be cleared before control returns to the caller.
    Why this matters: A leaked ``_current_message_id`` / ``_current_chat_id``
      causes the next request's :class:`TextDelta` / :class:`ActivityProgress`
      to publish with stale ids — silently corrupting downstream writes.
    Setup summary: Build an orchestrator with no default subscribers, subscribe
      a handler on ``stream_started`` that raises, fake the OpenAI client so
      ``complete_with_references_async`` would otherwise complete cleanly, and
      assert the outer error propagates while the per-request context is None.
    """
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_FakeStream([]))

    orchestrator = _build_orchestrator(client=fake_client)

    class _Boom(RuntimeError):
        pass

    async def _raising(_event: StreamStarted) -> None:
        raise _Boom("subscriber failed")

    orchestrator.bus.stream_started.subscribe(_raising)

    with pytest.raises(_Boom):
        await orchestrator.complete_with_references_async(
            messages=[{"role": "user", "content": "hi"}],
            model_name="test-model",
        )

    assert orchestrator._current_message_id is None
    assert orchestrator._current_chat_id is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completions__happy_path__clears_context_after_completion():
    """
    Purpose: Confirm the normal completion path also clears per-request context.
    Why this matters: Guards against the regression where the outer try/finally
      refactor accidentally skips the clear on the happy path.
    Setup summary: Drive a minimal fake stream through the orchestrator and
      assert the per-request ids are ``None`` after the call returns.
    """
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_FakeStream([]))

    orchestrator = _build_orchestrator(client=fake_client)
    await orchestrator.complete_with_references_async(
        messages=[{"role": "user", "content": "hi"}],
        model_name="test-model",
    )

    assert orchestrator._current_message_id is None
    assert orchestrator._current_chat_id is None
