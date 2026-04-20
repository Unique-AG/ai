"""Protocols for OpenAI Chat Completions stream handlers (``chat.completions.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from unique_toolkit.protocols.streaming import (
    StreamTextHandlerProtocol,
    StreamToolCallHandlerProtocol,
)

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk


class ChatCompletionTextHandlerProtocol(StreamTextHandlerProtocol, Protocol):
    """Accumulates text from ``ChatCompletionChunk`` and publishes flushes.

    Framework-specific text handler: inherits the role contract
    (:class:`StreamTextHandlerProtocol` — ``text_bus``, ``get_text``,
    lifecycle) and adds only the Chat Completions consumer method.
    """

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> None:
        """Process one chunk; publish :class:`TextFlushed` on flush boundaries."""
        ...


class ChatCompletionToolCallHandlerProtocol(StreamToolCallHandlerProtocol, Protocol):
    """Accumulates tool calls from ``ChatCompletionChunk``.

    Framework-specific tool-call handler: inherits the role contract
    (:class:`StreamToolCallHandlerProtocol` — ``get_tool_calls``,
    lifecycle) and adds only the Chat Completions consumer method.
    """

    async def on_chunk(self, event: ChatCompletionChunk) -> None: ...
