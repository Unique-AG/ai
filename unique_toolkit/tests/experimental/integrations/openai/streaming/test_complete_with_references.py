"""Tests for orchestrator-level behavior of the streaming
``ChatCompletionsCompleteWithReferences`` and ``ResponsesCompleteWithReferences``.

Focused on the invariants that event handlers/routers/subscribers cannot observe on
their own: per-request context cleanup, re-entry guards, and graceful handling
of subscriber/SDK failures at orchestrator boundaries.
"""

from __future__ import annotations

import asyncio
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
from unique_toolkit.experimental.integrations.openai.streaming.event_routing.chat_completions.complete_with_references import (
    ChatCompletionsCompleteWithReferences,
)
from unique_toolkit.experimental.integrations.openai.streaming.event_routing.events import (
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
        self.enter_calls = 0
        self.exit_calls = 0
        self.exit_exc_type: type[BaseException] | None = None

    async def __aenter__(self) -> "_FakeStream":
        self.enter_calls += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.exit_calls += 1
        self.exit_exc_type = exc_type
        return None

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk


def _build_orchestrator(
    *,
    client: Any,
) -> ChatCompletionsCompleteWithReferences:
    """Build an orchestrator with no default subscribers and an injected client."""
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.chat_completions.stream_event_router import (
        ChatCompletionStreamEventRouter,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.chat_completions.text_event_handler import (
        ChatCompletionTextEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.chat_completions.tool_call_event_handler import (
        ChatCompletionToolCallEventHandler,
    )

    router = ChatCompletionStreamEventRouter(
        text_event_handler=ChatCompletionTextEventHandler(replacers=[]),
        tool_call_event_handler=ChatCompletionToolCallEventHandler(),
    )
    return ChatCompletionsCompleteWithReferences(
        _settings_with_chat(),
        client=client,
        router=router,
        subscribers=(),
    )


def _build_responses_orchestrator(*, client: Any) -> Any:
    """Build a Responses orchestrator with no default subscribers."""
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.code_interpreter_event_handler import (
        ResponsesCodeInterpreterEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.complete_with_references import (
        ResponsesCompleteWithReferences,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.completed_event_handler import (
        ResponsesCompletedEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.stream_event_router import (
        ResponsesStreamEventRouter,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.text_delta_event_handler import (
        ResponsesTextDeltaEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.tool_call_event_handler import (
        ResponsesToolCallEventHandler,
    )

    router = ResponsesStreamEventRouter(
        text_event_handler=ResponsesTextDeltaEventHandler(replacers=[]),
        tool_call_event_handler=ResponsesToolCallEventHandler(),
        completed_event_handler=ResponsesCompletedEventHandler(),
        code_interpreter_event_handler=ResponsesCodeInterpreterEventHandler(),
    )
    return ResponsesCompleteWithReferences(
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
      causes the next request's :class:`TextUpdate` / :class:`ActivityProgress`
      to publish with stale ids — silently corrupting downstream writes.
    Setup summary: Build an orchestrator with no default subscribers, subscribe
      an event handler on ``stream_started`` that raises, fake the OpenAI client so
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
async def test_AI_chat_completions__concurrent_call__raises_reentry_error():
    """
    Purpose: A second concurrent ``complete_with_references_async`` on the
      same orchestrator must raise a clear re-entry error.
    Why this matters: Per-instance mutable state (``_current_*``, router
      accumulators) is not safe for overlapping requests. Dropping events
      silently (the previous behaviour) hid wiring bugs; a hard error
      surfaces the constraint.
    Setup summary: Drive a first call with a stream that blocks on an
      ``asyncio.Event`` so it stays in-flight; kick off a second call
      concurrently and assert it raises ``RuntimeError`` while the first
      still completes cleanly once released.
    """

    gate = asyncio.Event()

    class _BlockingStream:
        async def __aenter__(self) -> "_BlockingStream":
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            return None

        async def __aiter__(self):
            await gate.wait()
            # Never yield any chunks; once released we finalize cleanly.
            if False:
                yield None

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_BlockingStream())

    orchestrator = _build_orchestrator(client=fake_client)

    first = asyncio.create_task(
        orchestrator.complete_with_references_async(
            messages=[{"role": "user", "content": "hi"}],
            model_name="test-model",
        )
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    with pytest.raises(RuntimeError, match="concurrent"):
        await orchestrator.complete_with_references_async(
            messages=[{"role": "user", "content": "hi"}],
            model_name="test-model",
        )

    gate.set()
    await first
    assert orchestrator._in_flight is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completions__unsupported_protocol_kwargs__logged(caplog):
    """
    Purpose: ``timeout`` and ``start_text`` are accepted on the protocol but
      not forwarded to the OpenAI client; the orchestrator must log a warning
      when callers set them.
    Why this matters: Callers will assume ``timeout`` controls the HTTP
      request. A silent drop is a footgun; a warning makes the mismatch
      visible without breaking the protocol contract.
    Setup summary: Call with non-default values and assert the corresponding
      warnings were emitted.
    """
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_FakeStream([]))

    orchestrator = _build_orchestrator(client=fake_client)

    import logging

    with caplog.at_level(
        logging.WARNING,
        logger=(
            "unique_toolkit.experimental.integrations.openai.streaming.event_routing."
            "chat_completions.complete_with_references"
        ),
    ):
        await orchestrator.complete_with_references_async(
            messages=[{"role": "user", "content": "hi"}],
            model_name="test-model",
            timeout=1000,
            start_text="seed",
        )

    messages = [r.getMessage() for r in caplog.records]
    assert any("timeout=1000" in m for m in messages)
    assert any("start_text" in m for m in messages)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completions__final_response__includes_request_and_debug_info() -> (
    None
):
    """
    Purpose: Final ``LanguageModelStreamResponse.message`` keeps request and
      debug metadata supplied to the orchestrator.
    Why this matters: ``TextUpdate`` should stay narrow, but callers still need
      ``gpt_request`` and ``debug_info`` on the final message for audit/debug
      workflows.
    Setup summary: Drive an empty fake stream with explicit ``debug_info`` and
      assert the returned message contains the final metadata.
    """
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_FakeStream([]))
    orchestrator = _build_orchestrator(client=fake_client)

    response = await orchestrator.complete_with_references_async(
        messages=[{"role": "user", "content": "hi"}],
        model_name="test-model",
        debug_info={"trace_id": "abc"},
    )

    assert response.message.gpt_request == [{"role": "user", "content": "hi"}]
    assert response.message.debug_info == {"trace_id": "abc"}


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completions__event_handler_error__closes_openai_stream():
    """
    Purpose: Unexpected event-routing failures still exit the OpenAI stream context.
    Why this matters: The SDK stream owns the HTTP response; without
      ``__aexit__`` an exception from routing can leak the connection.
    Setup summary: Drive one fake chunk while ``router.on_event`` raises and
      assert the original exception propagates after the stream context exits.
    """

    class _Boom(RuntimeError):
        pass

    stream = _FakeStream([object()])
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=stream)
    orchestrator = _build_orchestrator(client=fake_client)
    orchestrator._router.on_event = AsyncMock(side_effect=_Boom("router failed"))

    with pytest.raises(_Boom):
        await orchestrator.complete_with_references_async(
            messages=[{"role": "user", "content": "hi"}],
            model_name="test-model",
        )

    assert stream.enter_calls == 1
    assert stream.exit_calls == 1
    assert stream.exit_exc_type is _Boom


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses__event_handler_error__closes_openai_stream():
    """
    Purpose: Responses API streams are also closed when event routing raises.
    Why this matters: ``client.responses.create(stream=True)`` returns an SDK
      stream that must deterministically release its HTTP connection on errors.
    Setup summary: Drive one fake event while ``router.on_event`` raises and
      assert the stream context manager observes the propagated exception.
    """

    class _Boom(RuntimeError):
        pass

    stream = _FakeStream([object()])
    fake_client = MagicMock()
    fake_client.responses.create = AsyncMock(return_value=stream)
    orchestrator = _build_responses_orchestrator(client=fake_client)
    orchestrator._router.on_event = AsyncMock(side_effect=_Boom("router failed"))

    with pytest.raises(_Boom):
        await orchestrator.complete_with_references_async(
            messages="hi",
            model_name="test-model",
        )

    assert stream.enter_calls == 1
    assert stream.exit_calls == 1
    assert stream.exit_exc_type is _Boom


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completions__text_flush_between_requests__is_logged(caplog):
    """
    Purpose: A ``TextFlushed`` arriving outside a request window is dropped
      *and* a warning is logged.
    Why this matters: The previous silent drop made wiring mistakes invisible
      (e.g. an event handler emitting a flush after the orchestrator cleared its
      context). A loud log surfaces those regressions in production.
    Setup summary: Instantiate the orchestrator, directly drive the adapter
      with the per-request context unset, and assert a warning is recorded.
    """
    import logging

    from unique_toolkit.experimental._internal.streaming import TextFlushed

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_FakeStream([]))
    orchestrator = _build_orchestrator(client=fake_client)

    with caplog.at_level(
        logging.WARNING,
        logger=(
            "unique_toolkit.experimental.integrations.openai.streaming.event_routing."
            "chat_completions.complete_with_references"
        ),
    ):
        await orchestrator._on_text_flushed(
            TextFlushed(full_text="late", original_text="late")
        )

    assert any("dropping TextFlushed" in r.getMessage() for r in caplog.records)


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


@pytest.mark.ai
def test_AI_chat_completions__client_without_subscribers__raises_type_error():
    """
    Purpose: Providing ``client`` without ``router`` and ``subscribers`` must
      raise ``TypeError`` rather than silently falling through to the default
      settings-driven construction for those two collaborators.
    Why this matters: The overload contract is deliberately "all three or
      none" — mixing a pre-built client with a default router or
      default-registered subscribers silently couples collaborators the
      caller never opted into.
    Setup summary: Try to instantiate with only ``client`` set and assert
      ``TypeError`` is raised; then instantiate with the complete
      instance-injection shape and assert it succeeds.
    """
    fake_client = MagicMock()

    with pytest.raises(TypeError, match="instance-injection"):
        ChatCompletionsCompleteWithReferences(  # type: ignore[reportCallIssue]
            _settings_with_chat(),
            client=fake_client,
        )

    with pytest.raises(TypeError, match="instance-injection"):
        ChatCompletionsCompleteWithReferences(  # type: ignore[reportCallIssue]
            _settings_with_chat(),
            client=fake_client,
            subscribers=(),
        )

    orchestrator = _build_orchestrator(client=fake_client)
    assert orchestrator is not None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completions__close__cancels_event_handler_bus_subscription():
    """
    Purpose: :meth:`close` must cancel the orchestrator's subscription on
      the router's text bus so it stops receiving :class:`TextFlushed`.
    Why this matters: The ``Subscription`` handle returned by
      :meth:`TypedEventBus.subscribe` was previously ignored; if a router
      outlived its orchestrator it would keep calling the stale adapter
      (holding references the caller expects released).
    Setup summary: Build an orchestrator, assert one event handler is registered
      on the router's text bus, call :meth:`close`, and assert the
      subscription was removed from the bus event handler list.
    """
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_FakeStream([]))
    orchestrator = _build_orchestrator(client=fake_client)

    event_handlers_before = list(orchestrator._router.text_bus._handlers)
    assert any(h == orchestrator._on_text_flushed for h in event_handlers_before)

    orchestrator.close()

    event_handlers_after = list(orchestrator._router.text_bus._handlers)
    assert not any(h == orchestrator._on_text_flushed for h in event_handlers_after)
