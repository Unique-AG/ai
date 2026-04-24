"""Protocols for OpenAI Responses API stream handlers (``responses.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from unique_toolkit.protocols.streaming import (
    ActivityProducer,
    AppendixProducer,
    StreamHandlerProtocol,
    StreamTextHandlerProtocol,
    StreamToolCallHandlerProtocol,
)

if TYPE_CHECKING:
    from openai.types.responses import (
        ResponseCompletedEvent,
        ResponseFunctionCallArgumentsDoneEvent,
        ResponseOutputItemAddedEvent,
        ResponseTextDeltaEvent,
    )

    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.code_interpreter_handler import (
        CodeInterpreterCallEvent,
    )
    from unique_toolkit.language_model.schemas import (
        LanguageModelTokenUsage,
        ResponseOutputItem,
    )


class ResponsesTextDeltaHandlerProtocol(StreamTextHandlerProtocol, Protocol):
    """Accumulates text from ``ResponseTextDeltaEvent`` and publishes flushes.

    Framework-specific text handler: inherits the role contract
    (:class:`StreamTextHandlerProtocol` — ``text_bus``, ``get_text``,
    lifecycle) and adds only the Responses consumer method.
    """

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> None:
        """Process one delta; publish :class:`TextFlushed` on non-empty deltas."""
        ...


class ResponsesToolCallHandlerProtocol(StreamToolCallHandlerProtocol, Protocol):
    """Accumulates function tool calls from Responses stream events.

    Framework-specific tool-call handler: inherits the role contract
    (:class:`StreamToolCallHandlerProtocol` — ``get_tool_calls``,
    lifecycle) and adds the Responses consumer pair (item-added +
    arguments-done).
    """

    async def on_output_item_added(
        self, event: ResponseOutputItemAddedEvent
    ) -> None: ...

    async def on_function_arguments_done(
        self, event: ResponseFunctionCallArgumentsDoneEvent
    ) -> None: ...


class ResponsesCompletedHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Extracts usage and output items from ``ResponseCompletedEvent``.

    Responses-only: Chat Completions surfaces usage inline on the final
    chunk, so no symmetric protocol exists for that API.
    """

    async def on_completed(self, event: ResponseCompletedEvent) -> None: ...

    def get_usage(self) -> LanguageModelTokenUsage | None: ...

    def get_output(self) -> list[ResponseOutputItem]: ...


class ResponsesCodeInterpreterHandlerProtocol(
    StreamHandlerProtocol,
    AppendixProducer,
    ActivityProducer,
    Protocol,
):
    """Accumulates code-interpreter activity as pure state.

    Composes three capabilities: :class:`StreamHandlerProtocol` for
    lifecycle, :class:`AppendixProducer` so the pipeline can aggregate
    its executed-code appendix alongside other handlers' contributions,
    and :class:`ActivityProducer` for the handler-owned
    ``activity_bus`` publishing :class:`ActivityProgressUpdate`. The
    only CI-specific member is :meth:`on_code_interpreter_event`, which
    consumes the OpenAI SDK's typed CI events.
    """

    async def on_code_interpreter_event(
        self, event: CodeInterpreterCallEvent
    ) -> None: ...
