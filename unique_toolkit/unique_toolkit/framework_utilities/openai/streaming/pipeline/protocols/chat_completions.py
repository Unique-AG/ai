"""Protocols for OpenAI Chat Completions stream handlers (``chat.completions.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .common import StreamHandlerProtocol, TextState

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

    from unique_toolkit.language_model.schemas import LanguageModelFunction


class ChatCompletionTextHandlerProtocol(Protocol):
    """Accumulates text from ``ChatCompletionChunk``.

    Pure state machine: no SDK, no bus, no knowledge of retrieved chunks.
    Returns a flush flag so the orchestrator can publish :class:`TextDelta`
    events at the handler-defined cadence.
    """

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> bool:
        """Process one chunk; return True iff a flush boundary was crossed."""
        ...

    async def on_stream_end(self) -> bool:
        """Flush replacer buffers; return True iff residual text was produced."""
        ...

    def reset(self) -> None: ...

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        ...


class ChatCompletionToolCallHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Accumulates tool calls from ``ChatCompletionChunk``."""

    async def on_chunk(self, event: ChatCompletionChunk) -> None: ...

    def get_tool_calls(self) -> list[LanguageModelFunction]: ...
