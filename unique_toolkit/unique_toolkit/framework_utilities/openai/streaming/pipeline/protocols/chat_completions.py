"""Protocols for OpenAI Chat Completions stream handlers (``chat.completions.create`` stream)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .common import StreamHandlerProtocol, TextState

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

    from unique_toolkit.language_model.schemas import LanguageModelFunction


class ChatCompletionTextHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Accumulates text from ``ChatCompletionChunk`` and emits SDK message events."""

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> None: ...

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        ...


class ChatCompletionToolCallHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Accumulates tool calls from ``ChatCompletionChunk``."""

    async def on_chunk(self, event: ChatCompletionChunk) -> None: ...

    def get_tool_calls(self) -> list[LanguageModelFunction]: ...
