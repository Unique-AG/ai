"""Protocols for OpenAI Chat Completions stream handlers (``chat.completions.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .common import StreamHandlerProtocol, TextFlushed, TextState

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

    from unique_toolkit._common.event_bus import TypedEventBus
    from unique_toolkit.language_model.schemas import LanguageModelFunction


class ChatCompletionTextHandlerProtocol(Protocol):
    """Accumulates text from ``ChatCompletionChunk`` and publishes flushes.

    Pure state machine: no SDK, no outer bus, no knowledge of retrieved
    chunks. Owns a typed :class:`TypedEventBus` carrying
    :class:`TextFlushed`; external subscribers (typically the
    orchestrator) adapt those into full :class:`TextDelta` events by
    attaching request context.
    """

    @property
    def text_bus(self) -> TypedEventBus[TextFlushed]:
        """Handler-owned bus publishing :class:`TextFlushed` at flush boundaries."""
        ...

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> None:
        """Process one chunk; publish :class:`TextFlushed` on flush boundaries."""
        ...

    async def on_stream_end(self) -> None:
        """Flush replacer buffers; publish a final :class:`TextFlushed` if needed."""
        ...

    def reset(self) -> None: ...

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        ...


class ChatCompletionToolCallHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Accumulates tool calls from ``ChatCompletionChunk``."""

    async def on_chunk(self, event: ChatCompletionChunk) -> None: ...

    def get_tool_calls(self) -> list[LanguageModelFunction]: ...
