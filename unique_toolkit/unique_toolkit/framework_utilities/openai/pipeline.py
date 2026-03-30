from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any, Protocol

import unique_sdk
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)

from unique_toolkit.app.unique_settings import UniqueSettings

_LOGGER = logging.getLogger(__name__)

Replacement = str | Callable[[re.Match[str]], str]


class AsyncPipelinePart(Protocol):
    """Async stream segment; ``process`` is an async generator (use plain ``def`` in the Protocol)."""

    def process(self, stream: AsyncIterator[Any]) -> AsyncIterator[Any]: ...


class StreamingTextState(Protocol):
    @property
    def original_text(self) -> str: ...

    @property
    def processed_text(self) -> str: ...


class ChatCompletionChunkPipelinePart(AsyncPipelinePart):
    def __init__(self):
        self._full_text = ""
        self._tool_calls: list[ChatCompletionMessageFunctionToolCall] = []

    @property
    def full_text(self) -> str:
        return self._full_text

    async def process(
        self, stream: AsyncIterator[ChatCompletionChunk]
    ) -> AsyncIterator[str]:
        async for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content is not None:
                self._full_text += delta.content or ""

            if delta.tool_calls:
                for tc in delta.tool_calls or []:
                    if tc.index not in self._tool_calls:
                        self._tool_calls[tc.index] = (
                            ChatCompletionMessageFunctionToolCall(
                                id=tc.id or "",
                                function=Function(
                                    name="",
                                    arguments="",
                                ),
                                type="function",
                            )
                        )

                    if tc.id is not None:
                        self._tool_calls[tc.index].id = tc.id or ""

                    if tc.function:
                        if tc.function.name:
                            self._tool_calls[tc.index].function.name = (
                                tc.function.name or ""
                            )
                        if tc.function.arguments:
                            self._tool_calls[tc.index].function.arguments += (
                                tc.function.arguments or ""
                            )

            if choice.finish_reason == "tool_calls":
                break

            yield delta.content or ""


class PatternReplacementPipelinePart(AsyncPipelinePart):
    """Applies regex replacements on an async string stream.

    Buffers up to ``max_match_length`` trailing characters so partial matches
    at chunk boundaries are not emitted until complete; after the stream ends,
    the remainder is flushed.
    """

    def __init__(
        self,
        replacements: Sequence[tuple[str | re.Pattern[str], Replacement]],
        max_match_length: int,
    ) -> None:
        self._replacements = [
            (re.compile(p) if isinstance(p, str) else p, repl)
            for p, repl in replacements
        ]
        self._max_match_length = max_match_length
        self._buffer = ""
        self._original_text = ""
        self._processed_text = ""

    @property
    def original_text(self) -> str:
        return self._original_text

    @property
    def processed_text(self) -> str:
        return self._processed_text

    async def process(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
        async for text in stream:
            self._original_text += text
            new_delta = self._process_delta(text)
            self._processed_text += new_delta
            yield new_delta
        final = self._flush_buffer()
        self._processed_text += final
        yield final

    def _process_delta(self, delta: str) -> str:
        self._buffer += delta

        if self._max_match_length == 0:
            released = self._buffer
            self._buffer = ""
            return released

        self._buffer = self._apply_replacements(self._buffer)
        safe_end = max(0, len(self._buffer) - self._max_match_length)
        released = self._buffer[:safe_end]
        self._buffer = self._buffer[safe_end:]
        return released

    def _flush_buffer(self) -> str:
        self._buffer = self._apply_replacements(self._buffer)
        released = self._buffer
        self._buffer = ""
        return released

    def _apply_replacements(self, text: str) -> str:
        for pattern, replacement in self._replacements:
            text = pattern.sub(replacement, text)
        return text


class ChatMessageEventPipelinePart(AsyncPipelinePart):
    """Passes through a string stream while updating the chat message via the SDK.

    Aligns with :class:`~unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completion_sdk_persistence.ChatCompletionSdkPersistence` and :func:`~unique_toolkit.framework_utilities.openai.streaming.stream_to_message.stream_chat_completions_to_message`:
    each emission (or every *n* chunks when ``throttled``) calls
    ``unique_sdk.Message.create_event_async`` with cumulative ``text`` and
    ``originalText``.

    When chained after :class:`PatternReplacementPipelinePart`, pass that instance as
    ``text_state`` so ``originalText`` reflects the raw model stream and ``text`` the
    post-replacement content. Without ``text_state``, incoming deltas are accumulated
    and used for both fields.
    """

    def __init__(
        self,
        unique_settings: UniqueSettings,
        *,
        send_every_n_events: int = 1,
    ) -> None:
        self._settings = unique_settings
        self._send_every_n_events = max(1, send_every_n_events)
        self._full_text = ""
        self._stream_index = 0

        if unique_settings.context.chat is None:
            raise ValueError("Chat context is required")

    async def process(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
        async for delta in stream:
            self._full_text += delta
            self._stream_index += 1
            if self._stream_index % self._send_every_n_events == 0:
                await self._emit_event()
            yield delta

        await self._emit_event()

    async def _emit_event(self) -> None:
        chat = self._settings.context.chat
        assert chat is not None

        await unique_sdk.Message.create_event_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            **unique_sdk.Message.CreateEventParams(
                chatId=chat.chat_id,
                messageId=chat.last_assistant_message_id,
                text=self._full_text,
            ),
        )
