"""Protocols for OpenAI Responses API stream handlers (``responses.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .common import (
    ActivityProgressProducer,
    AppendixProducer,
    StreamHandlerProtocol,
    TextState,
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
        LanguageModelFunction,
        LanguageModelTokenUsage,
        ResponseOutputItem,
    )


class ResponsesTextDeltaHandlerProtocol(Protocol):
    """Accumulates text from ``ResponseTextDeltaEvent``.

    Pure state machine: no SDK, no bus, no knowledge of retrieved chunks.
    Returns a flush flag so the orchestrator can publish :class:`TextDelta`
    events when observable text was produced.
    """

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> bool:
        """Process one delta; return True iff observable text was produced."""
        ...

    async def on_stream_end(self) -> bool:
        """Flush replacer buffers; return True iff residual text was produced."""
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
    ActivityProgressProducer,
    AppendixProducer,
    Protocol,
):
    """Accumulates code-interpreter activity as pure state.

    Inherits the generic :class:`ActivityProgressProducer` and
    :class:`AppendixProducer` capability protocols so the pipeline picks
    up its contributions (progress updates, executed-code appendix)
    uniformly with any other handler that exposes the same shapes — no
    CI-specific wiring in the pipeline. The only CI-specific member is
    :meth:`on_code_interpreter_event`, which consumes the OpenAI SDK's
    typed CI events.
    """

    async def on_code_interpreter_event(
        self, event: CodeInterpreterCallEvent
    ) -> None: ...
