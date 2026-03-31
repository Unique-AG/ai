"""Streaming pipeline protocols.

:class:`StreamHandlerProtocol` provides lifecycle methods shared by every
event handler.  Per-event-group protocols inherit from it and add typed
event methods and result getters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
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


# ---------------------------------------------------------------------------
# Handler protocols
# ---------------------------------------------------------------------------


class StreamHandlerProtocol(Protocol):
    """Lifecycle methods shared by every event handler."""

    async def on_stream_end(self) -> None:
        """Finalize after the stream is exhausted (flush buffers, final SDK calls)."""
        ...

    def reset(self) -> None:
        """Clear all per-run state for reuse."""
        ...


# --- Responses API handler protocols ---


class ResponsesTextDeltaHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Accumulates text from ``ResponseTextDeltaEvent`` and emits SDK message events."""

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> None: ...
    def get_text(self) -> tuple[str, str]:
        """Return ``(full_text, original_text)``."""
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


class ResponsesCodeInterpreterHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Manages ``MessageLog`` lifecycle for code interpreter calls (pure side-effects)."""

    async def on_code_interpreter_event(
        self, event: CodeInterpreterCallEvent
    ) -> None: ...


# --- Chat Completions handler protocols ---


class ChatCompletionTextHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Accumulates text from ``ChatCompletionChunk`` and emits SDK message events."""

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> None: ...
    def get_text(self) -> tuple[str, str]:
        """Return ``(full_text, original_text)``."""
        ...


class ChatCompletionToolCallHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Accumulates tool calls from ``ChatCompletionChunk``."""

    async def on_chunk(self, event: ChatCompletionChunk) -> None: ...
    def get_tool_calls(self) -> list[LanguageModelFunction]: ...
