"""Handler for Chat Completion tool call deltas — accumulates tool calls."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)

from unique_toolkit.language_model.schemas import LanguageModelFunction

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

_LOGGER = logging.getLogger(__name__)


class ChatCompletionToolCallHandler:
    """Accumulates function tool calls from ``ChatCompletionChunk`` events.

    Private state: ``_tool_calls`` indexed by ``tc.index``.
    """

    def __init__(self) -> None:
        self._tool_calls: dict[int, ChatCompletionMessageFunctionToolCall] = {}

    async def on_chunk(self, event: ChatCompletionChunk) -> None:
        if len(event.choices) == 0:
            return
        delta = event.choices[0].delta
        if not delta.tool_calls:
            return

        for tc in delta.tool_calls:
            if tc.index not in self._tool_calls:
                self._tool_calls[tc.index] = ChatCompletionMessageFunctionToolCall(
                    id=tc.id or "",
                    function=Function(name="", arguments=""),
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

    def get_tool_calls(self) -> list[LanguageModelFunction]:
        result: list[LanguageModelFunction] = []
        for tc in (self._tool_calls[i] for i in sorted(self._tool_calls)):
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
            result.append(
                LanguageModelFunction(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments,
                )
            )
        return result

    async def on_stream_end(self) -> None:
        pass

    def reset(self) -> None:
        self._tool_calls = {}
