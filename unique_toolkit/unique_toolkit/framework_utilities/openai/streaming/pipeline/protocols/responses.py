"""Protocols for OpenAI Responses API stream handlers (``responses.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .common import (
    ActivityProgressUpdate,
    AppendixProducer,
    StreamHandlerProtocol,
    TextFlushed,
    TextState,
)

if TYPE_CHECKING:
    from openai.types.responses import (
        ResponseCompletedEvent,
        ResponseFunctionCallArgumentsDoneEvent,
        ResponseOutputItemAddedEvent,
        ResponseTextDeltaEvent,
    )

    from unique_toolkit._common.event_bus import TypedEventBus
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.code_interpreter_handler import (
        CodeInterpreterCallEvent,
    )
    from unique_toolkit.language_model.schemas import (
        LanguageModelFunction,
        LanguageModelTokenUsage,
        ResponseOutputItem,
    )


class ResponsesTextDeltaHandlerProtocol(Protocol):
    """Accumulates text from ``ResponseTextDeltaEvent`` and publishes flushes.

    Pure state machine: no SDK, no outer bus, no knowledge of retrieved
    chunks. Owns a typed :class:`TypedEventBus` carrying
    :class:`TextFlushed`; external subscribers (typically the
    orchestrator) adapt those into full :class:`TextDelta` events.
    """

    @property
    def flush_bus(self) -> TypedEventBus[TextFlushed]:
        """Handler-owned bus publishing :class:`TextFlushed` on each delta."""
        ...

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> None:
        """Process one delta; publish :class:`TextFlushed` on non-empty deltas."""
        ...

    async def on_stream_end(self) -> None:
        """Flush replacer buffers; publish a final :class:`TextFlushed` if needed."""
        ...

    def reset(self) -> None: ...

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        ...


class ResponsesToolCallHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Accumulates function tool calls from Responses stream events."""

    async def on_output_item_added(
        self, event: ResponseOutputItemAddedEvent
    ) -> None: ...

    async def on_function_arguments_done(
        self, event: ResponseFunctionCallArgumentsDoneEvent
    ) -> None: ...

    def get_tool_calls(self) -> list[LanguageModelFunction]: ...


class ResponsesCompletedHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Extracts usage and output items from ``ResponseCompletedEvent``."""

    async def on_completed(self, event: ResponseCompletedEvent) -> None: ...

    def get_usage(self) -> LanguageModelTokenUsage | None: ...

    def get_output(self) -> list[ResponseOutputItem]: ...


class ResponsesCodeInterpreterHandlerProtocol(
    StreamHandlerProtocol,
    AppendixProducer,
    Protocol,
):
    """Accumulates code-interpreter activity as pure state.

    Owns a typed :class:`TypedEventBus` carrying
    :class:`ActivityProgressUpdate` for tool-activity progress
    transitions (:attr:`progress_bus`), and inherits the generic
    :class:`AppendixProducer` capability so the pipeline can aggregate
    its executed-code appendix alongside any other handler's
    contributions. The only CI-specific member is
    :meth:`on_code_interpreter_event`, which consumes the OpenAI SDK's
    typed CI events.
    """

    @property
    def progress_bus(self) -> TypedEventBus[ActivityProgressUpdate]:
        """Handler-owned bus publishing progress updates per state transition."""
        ...

    async def on_code_interpreter_event(
        self, event: CodeInterpreterCallEvent
    ) -> None: ...
