"""Handler for Responses function tool call events — accumulates tool calls."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai.types.responses import (
        ResponseFunctionCallArgumentsDoneEvent,
        ResponseOutputItemAddedEvent,
    )

from unique_toolkit.language_model.schemas import LanguageModelFunction

_LOGGER = logging.getLogger(__name__)


class ResponsesToolCallHandler:
    """Accumulates function tool calls from ``ResponseOutputItemAddedEvent``
    and ``ResponseFunctionCallArgumentsDoneEvent``.

    Private state: ``_function_name_by_item_id``, ``_tool_calls``.
    """

    def __init__(self) -> None:
        self._function_name_by_item_id: dict[str, str] = {}
        self._tool_calls: list[LanguageModelFunction] = []

    async def on_output_item_added(self, event: ResponseOutputItemAddedEvent) -> None:
        from openai.types.responses.response_function_tool_call_item import (
            ResponseFunctionToolCallItem,
        )

        item = event.item
        if isinstance(item, ResponseFunctionToolCallItem):
            self._function_name_by_item_id[item.id] = item.name

    async def on_function_arguments_done(
        self, event: ResponseFunctionCallArgumentsDoneEvent
    ) -> None:
        self._tool_calls.append(
            _language_model_function_from_arguments_done(
                event, name_by_item_id=self._function_name_by_item_id
            )
        )

    def get_tool_calls(self) -> list[LanguageModelFunction]:
        return list(self._tool_calls)

    async def on_stream_end(self) -> None:
        pass

    def reset(self) -> None:
        self._function_name_by_item_id = {}
        self._tool_calls = []


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

    Older SDKs omit ``name`` on ``ResponseFunctionCallArgumentsDoneEvent``;
    newer releases include it.
    """
    name_on_event = getattr(event, "name", None)
    if isinstance(name_on_event, str) and name_on_event:
        return name_on_event
    return name_by_item_id.get(event.item_id, "")
