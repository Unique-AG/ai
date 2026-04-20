"""Tests for ``ResponsesTextDeltaHandler`` — accumulation and flushing rules
for the OpenAI Responses streaming variant.
"""

from __future__ import annotations

import pytest

from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.text_delta_handler import (
    ResponsesTextDeltaHandler,
)
from unique_toolkit.protocols.streaming import TextFlushed


class _TrailingFlushReplacer:
    """Replacer that emits a fixed trailing suffix only on ``flush()``."""

    def __init__(self, trailing: str) -> None:
        self._trailing = trailing

    def process(self, text: str) -> str:
        return text

    def flush(self) -> str:
        out = self._trailing
        self._trailing = ""
        return out


def _delta(text: str):
    from openai.types.responses import ResponseTextDeltaEvent

    return ResponseTextDeltaEvent.model_construct(
        type="response.output_text.delta",
        delta=text,
        item_id="it-1",
        output_index=0,
        content_index=0,
        sequence_number=0,
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_text_delta_handler__on_stream_end__does_not_publish_trailing_flush():
    """
    Purpose: ``on_stream_end`` drains replacer residuals into internal state
      without publishing a trailing :class:`TextFlushed`.
    Why this matters: The orchestrator publishes :class:`StreamEnded` with
      the authoritative ``full_text`` immediately after ``on_stream_end``.
      A trailing flush duplicated that write through the SDK.
    Setup summary: Register a replacer that only surfaces its text on
      ``flush()``, drive one non-empty delta, call ``on_stream_end``, and
      assert no new event fired while ``full_text`` includes the residual.
    """
    replacer = _TrailingFlushReplacer(trailing="!")
    handler = ResponsesTextDeltaHandler(replacers=[replacer])  # type: ignore[list-item]
    received: list[TextFlushed] = []
    handler.text_bus.subscribe(received.append)

    await handler.on_text_delta(_delta("hi"))
    assert len(received) == 1

    await handler.on_stream_end()

    assert len(received) == 1
    assert handler.get_text().full_text == "hi!"
