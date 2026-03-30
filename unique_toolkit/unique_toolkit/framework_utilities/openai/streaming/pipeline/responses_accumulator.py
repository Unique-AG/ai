"""Default fold for OpenAI Responses API stream events → :class:`LanguageModelStreamResponse`."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime

from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItem,
    ResponseOutputItemAddedEvent,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
)
from openai.types.responses.response_function_tool_call_item import (
    ResponseFunctionToolCallItem,
)

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelStreamResponse,
    LanguageModelTokenUsage,
    ResponsesLanguageModelStreamResponse,
)

_LOGGER = logging.getLogger(__name__)

_ACCUMULATOR_FINALIZED_ERROR = (
    "Stream accumulator has already produced a result for this fold. Call reset() "
    "before applying more events, building again, or reusing this instance after a "
    "manual build_stream_result()."
)


class ResponsesStreamAccumulator:
    """Accumulates text, function tool completions, and usage from a Responses stream.

    Handles a focused subset of :class:`ResponseStreamEvent` that maps cleanly to
    :class:`LanguageModelStreamResponse`. Other event types are ignored; extend
    this class if you need reasoning deltas, MCP, web search, etc.
    """

    __slots__ = (
        "_aggregated_text",
        "_finalized",
        "_function_name_by_item_id",
        "_output",
        "_tool_calls",
        "_usage",
    )

    def __init__(self) -> None:
        self._aggregated_text: str = ""
        self._finalized: bool = False
        self._function_name_by_item_id: dict[str, str] = {}
        self._output: list[ResponseOutputItem] = []
        self._tool_calls: list[LanguageModelFunction] = []
        self._usage: LanguageModelTokenUsage | None = None

    def reset(self) -> None:
        """Clear fold state and the finalized guard (see :class:`StreamAccumulatorProtocol`)."""
        self._aggregated_text = ""
        self._finalized = False
        self._function_name_by_item_id = {}
        self._output = []
        self._tool_calls = []
        self._usage = None

    @property
    def aggregated_text(self) -> str:
        return self._aggregated_text

    @property
    def tool_calls(self) -> list[LanguageModelFunction]:
        return list(self._tool_calls)

    @property
    def usage(self) -> LanguageModelTokenUsage | None:
        return self._usage

    def apply(self, event: ResponseStreamEvent) -> None:
        if self._finalized:
            raise RuntimeError(_ACCUMULATOR_FINALIZED_ERROR)
        if isinstance(event, ResponseTextDeltaEvent):
            self._aggregated_text += event.delta
            return
        if isinstance(event, ResponseOutputItemAddedEvent):
            item = event.item
            if isinstance(item, ResponseFunctionToolCallItem):
                self._function_name_by_item_id[item.id] = item.name
            return
        if isinstance(event, ResponseFunctionCallArgumentsDoneEvent):
            self._tool_calls.append(
                _language_model_function_from_arguments_done(
                    event,
                    name_by_item_id=self._function_name_by_item_id,
                )
            )
            return
        if isinstance(event, ResponseCompletedEvent):
            self._usage = _language_model_token_usage_from_completed(event)
            if event.response.output is not None:
                self._output = list(event.response.output)
            return

    def build_stream_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        created_at: datetime,
    ) -> LanguageModelStreamResponse:
        if self._finalized:
            raise RuntimeError(_ACCUMULATOR_FINALIZED_ERROR)
        message = ChatMessage(
            id=message_id,
            chat_id=chat_id,
            role=ChatMessageRole.ASSISTANT,
            text=self._aggregated_text,
            original_text=self._aggregated_text,
            created_at=created_at,
        )
        tool_calls = self._tool_calls if self._tool_calls else None
        result = LanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls,
            usage=self._usage,
        )
        self._finalized = True
        return result

    def build_language_model_stream_response(
        self,
        *,
        message_id: str,
        chat_id: str,
        created_at: datetime,
    ) -> LanguageModelStreamResponse:
        """Same as :meth:`build_stream_result` — descriptive alias for Responses callers."""
        return self.build_stream_result(
            message_id=message_id,
            chat_id=chat_id,
            created_at=created_at,
        )

    def build_responses_stream_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        created_at: datetime,
    ) -> ResponsesLanguageModelStreamResponse:
        """Build result including the full ``output`` list from the completed response.

        Use this instead of :meth:`build_stream_result` when the caller
        needs access to code-interpreter calls, container files, or other
        Responses-specific output items.
        """
        if self._finalized:
            raise RuntimeError(_ACCUMULATOR_FINALIZED_ERROR)

        message = ChatMessage(
            id=message_id,
            chat_id=chat_id,
            role=ChatMessageRole.ASSISTANT,
            text=self._aggregated_text,
            original_text=self._aggregated_text,
            created_at=created_at,
        )
        tool_calls = self._tool_calls if self._tool_calls else None
        result = ResponsesLanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls,
            usage=self._usage,
            output=self._output,
        )
        self._finalized = True
        return result


def _language_model_function_from_arguments_done(
    event: ResponseFunctionCallArgumentsDoneEvent,
    *,
    name_by_item_id: Mapping[str, str],
) -> LanguageModelFunction:
    fn_name = _resolve_function_tool_name(event, name_by_item_id)
    arguments: dict[str, object] | None
    raw = event.arguments.strip()
    if not raw:
        arguments = None
    else:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            _LOGGER.warning(
                "Function call arguments JSON decode failed (item_id=%s, name=%s)",
                event.item_id,
                fn_name,
            )
            arguments = None
        else:
            arguments = parsed if isinstance(parsed, dict) else {"_": parsed}

    return LanguageModelFunction(
        id=event.item_id,
        name=fn_name,
        arguments=arguments,
    )


def _resolve_function_tool_name(
    event: ResponseFunctionCallArgumentsDoneEvent,
    name_by_item_id: Mapping[str, str],
) -> str:
    """Resolve tool name across OpenAI Python SDK versions.

    Older SDKs omit ``name`` on :class:`ResponseFunctionCallArgumentsDoneEvent`;
    newer releases include it. When absent, use ``response.output_item.added``
    (see :class:`ResponseFunctionToolCallItem`).
    """
    name_on_event = getattr(event, "name", None)
    if isinstance(name_on_event, str) and name_on_event:
        return name_on_event
    return name_by_item_id.get(event.item_id, "")


def _language_model_token_usage_from_completed(
    event: ResponseCompletedEvent,
) -> LanguageModelTokenUsage | None:
    usage = event.response.usage
    if usage is None:
        return None
    return LanguageModelTokenUsage(
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )
