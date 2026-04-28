"""Protocols for OpenAI Chat Completions stream event handlers (``chat.completions.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from unique_toolkit.experimental.components.streaming import (
    StreamTextEventHandlerProtocol,
    StreamToolCallEventHandlerProtocol,
    UsageProducer,
)

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk


class ChatCompletionTextEventHandlerProtocol(
    StreamTextEventHandlerProtocol, UsageProducer, Protocol
):
    """Accumulates text and usage from ``ChatCompletionChunk`` events.

    Framework-specific text event handler: inherits the role contract
    (:class:`StreamTextEventHandlerProtocol` — ``text_bus``, ``get_text``,
    lifecycle), :class:`UsageProducer` for optional terminal usage, and
    adds only the Chat Completions consumer method.
    """

    async def on_chunk(self, event: ChatCompletionChunk) -> None:
        """Process one chunk; publish :class:`TextFlushed` on flush boundaries."""
        ...


class ChatCompletionToolCallEventHandlerProtocol(
    StreamToolCallEventHandlerProtocol, Protocol
):
    """Accumulates tool calls from ``ChatCompletionChunk``.

    Framework-specific tool-call event handler: inherits the role contract
    (:class:`StreamToolCallEventHandlerProtocol` — ``get_tool_calls``,
    lifecycle) and adds only the Chat Completions consumer method.
    """

    async def on_chunk(self, event: ChatCompletionChunk) -> None: ...
