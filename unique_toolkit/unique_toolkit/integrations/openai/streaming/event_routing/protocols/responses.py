"""Protocols for OpenAI Responses API stream event handlers (``responses.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from unique_toolkit._internal.streaming import (
    ActivityProducer,
    StreamEventHandlerProtocol,
    StreamTextEventHandlerProtocol,
    StreamToolCallEventHandlerProtocol,
    UsageProducer,
)

if TYPE_CHECKING:
    from openai.types.responses import (
        ResponseCompletedEvent,
        ResponseFunctionCallArgumentsDoneEvent,
        ResponseOutputItemAddedEvent,
        ResponseTextDeltaEvent,
    )

    from unique_toolkit.integrations.openai.streaming.event_routing.responses.code_interpreter_event_handler import (
        CodeInterpreterCallEvent,
    )
    from unique_toolkit.language_model.schemas import (
        ResponseOutputItem,
    )


class ResponsesTextDeltaEventHandlerProtocol(StreamTextEventHandlerProtocol, Protocol):
    """Accumulates text from ``ResponseTextDeltaEvent`` and publishes flushes.

    Framework-specific text event handler: inherits the role contract
    (:class:`StreamTextEventHandlerProtocol` — ``text_bus``, ``get_text``,
    lifecycle) and adds only the Responses consumer method.
    """

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> None:
        """Process one delta; publish :class:`TextFlushed` on non-empty deltas."""
        ...


class ResponsesToolCallEventHandlerProtocol(
    StreamToolCallEventHandlerProtocol, Protocol
):
    """Accumulates function tool calls from Responses stream events.

    Framework-specific tool-call event handler: inherits the role contract
    (:class:`StreamToolCallEventHandlerProtocol` — ``get_tool_calls``,
    lifecycle) and adds the Responses consumer pair (item-added +
    arguments-done).
    """

    async def on_output_item_added(
        self, event: ResponseOutputItemAddedEvent
    ) -> None: ...

    async def on_function_arguments_done(
        self, event: ResponseFunctionCallArgumentsDoneEvent
    ) -> None: ...


class ResponsesCompletedEventHandlerProtocol(
    StreamEventHandlerProtocol, UsageProducer, Protocol
):
    """Extracts usage and output items from ``ResponseCompletedEvent``.

    Responses-only: Chat Completions surfaces usage inline on the final
    chunk, so only the event consumer and output accessor are specific to
    this protocol. Token usage itself is shared via
    :class:`UsageProducer`.
    """

    async def on_completed(self, event: ResponseCompletedEvent) -> None: ...

    def get_output(self) -> list[ResponseOutputItem]: ...


class ResponsesCodeInterpreterEventHandlerProtocol(
    StreamEventHandlerProtocol,
    ActivityProducer,
    Protocol,
):
    """Accumulates code-interpreter activity as pure state.

    Composes :class:`StreamEventHandlerProtocol` for lifecycle,
    :class:`ActivityProducer` for the event-handler-owned ``activity_bus``
    publishing :class:`ActivityProgressUpdate`, and the only CI-specific
    member :meth:`on_code_interpreter_event`, which consumes the OpenAI SDK's
    typed CI events. Executed code is not appended to the persisted assistant
    message.
    """

    async def on_code_interpreter_event(
        self, event: CodeInterpreterCallEvent
    ) -> None: ...
