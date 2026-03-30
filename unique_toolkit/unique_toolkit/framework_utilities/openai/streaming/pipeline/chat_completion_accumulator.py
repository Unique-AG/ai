"""Fold :class:`ChatCompletionChunk` streams into :class:`LanguageModelStreamResponse`."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime

from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelStreamResponse,
)

_LOGGER = logging.getLogger(__name__)


class ChatCompletionStreamAccumulator:
    """Accumulates assistant text and function tool calls from chat completion chunks."""

    __slots__ = ("_full_text", "_tool_calls")

    def __init__(self) -> None:
        self._full_text: str = ""
        self._tool_calls: dict[int, ChatCompletionMessageFunctionToolCall] = {}

    def reset(self) -> None:
        self._full_text = ""
        self._tool_calls = {}

    @property
    def full_text(self) -> str:
        return self._full_text

    def chat_completion_tool_calls(self) -> list[ChatCompletionMessageFunctionToolCall]:
        return [self._tool_calls[i] for i in sorted(self._tool_calls)]

    def apply(self, event: ChatCompletionChunk) -> None:
        if len(event.choices) == 0:
            return
        choice = event.choices[0]
        delta = choice.delta

        if delta.content is not None:
            self._full_text += delta.content or ""

        if delta.tool_calls:
            for tc in delta.tool_calls:
                if tc.index not in self._tool_calls:
                    self._tool_calls[tc.index] = ChatCompletionMessageFunctionToolCall(
                        id=tc.id or "",
                        function=Function(
                            name="",
                            arguments="",
                        ),
                        type="function",
                    )

                if tc.id is not None:
                    self._tool_calls[tc.index].id = tc.id

                if tc.function:
                    if tc.function.name:
                        self._tool_calls[tc.index].function.name = tc.function.name
                    if tc.function.arguments:
                        self._tool_calls[tc.index].function.arguments += (
                            tc.function.arguments or ""
                        )

    def build_stream_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        created_at: datetime,
    ) -> LanguageModelStreamResponse:
        tool_calls_lm: list[LanguageModelFunction] = []
        for tc in self.chat_completion_tool_calls():
            arguments: dict[str, object] | None
            raw = tc.function.arguments.strip()
            if not raw:
                arguments = None
            else:
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    _LOGGER.warning(
                        "Tool call arguments JSON decode failed (tool_id=%s, name=%s)",
                        tc.id,
                        tc.function.name,
                    )
                    arguments = None
                else:
                    arguments = parsed if isinstance(parsed, dict) else {"_": parsed}

            tool_calls_lm.append(
                LanguageModelFunction(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments,
                )
            )

        message = ChatMessage(
            id=message_id,
            chat_id=chat_id,
            role=ChatMessageRole.ASSISTANT,
            text=self._full_text,
            created_at=created_at,
        )

        return LanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls_lm if tool_calls_lm else None,
        )


async def iter_chat_completion_chunks_until_tool_calls(
    stream: AsyncIterator[ChatCompletionChunk],
) -> AsyncIterator[ChatCompletionChunk]:
    """Yield chunks until ``finish_reason == \"tool_calls\"`` (matches legacy loop)."""
    async for chunk in stream:
        yield chunk
        if not chunk.choices:
            continue
        if chunk.choices[0].finish_reason == "tool_calls":
            break
