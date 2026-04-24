"""Tests for ``ChatCompletionTextHandler`` — Chat Completion text delta
accumulation, flush throttling, and bus publishing semantics.
"""

from __future__ import annotations

import pytest
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)

from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.text_handler import (
    ChatCompletionTextHandler,
)
from unique_toolkit.protocols.streaming import TextFlushed


def _chunk(
    *,
    content: str | None = None,
    tool_calls: list[ChoiceDeltaToolCall] | None = None,
    no_choices: bool = False,
) -> ChatCompletionChunk:
    choices = (
        []
        if no_choices
        else [
            Choice.model_construct(
                index=0,
                delta=ChoiceDelta.model_construct(
                    content=content, tool_calls=tool_calls
                ),
            )
        ]
    )
    return ChatCompletionChunk.model_construct(
        id="chunk",
        choices=choices,
        created=0,
        model="gpt-test",
        object="chat.completion.chunk",
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_text_handler__send_every_n_events__counts_content_chunks_only():
    """
    Purpose: Throttling must key off content-bearing chunks, not the raw chunk
      position on the wire.
    Why this matters: OpenAI streams can lead with role-only or tool-call-only
      chunks. If those advanced the throttle counter, ``send_every_n_events=2``
      would emit on the wrong content boundary (or skip the first content
      chunk entirely) — producing irregular or missing SDK writes.
    Setup summary: Build a handler with ``send_every_n_events=2``; feed a
      tool-call-only chunk, an empty-choices chunk, then two content chunks;
      assert exactly one :class:`TextFlushed` fires and it corresponds to the
      *second* content chunk.
    """
    handler = ChatCompletionTextHandler(replacers=[], send_every_n_events=2)
    received: list[TextFlushed] = []
    handler.text_bus.subscribe(received.append)

    tool_only = _chunk(
        tool_calls=[
            ChoiceDeltaToolCall.model_construct(
                index=0,
                id="tc-1",
                function=ChoiceDeltaToolCallFunction.model_construct(
                    name="lookup", arguments=""
                ),
                type="function",
            )
        ]
    )
    empty_choices = _chunk(no_choices=True)
    first_content = _chunk(content="a")
    second_content = _chunk(content="b")

    await handler.on_chunk(tool_only)
    await handler.on_chunk(empty_choices)
    await handler.on_chunk(first_content)
    assert received == []
    await handler.on_chunk(second_content)
    assert len(received) == 1
    assert received[0].full_text == "ab"
    assert received[0].chunk_index == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_text_handler__reset__resets_content_chunk_index():
    """
    Purpose: ``reset`` clears the content-chunk counter so the next request
      starts throttling from zero.
    Why this matters: A persistent counter would delay the first flush of the
      next request depending on the chunk count of the previous one.
    Setup summary: Send one content chunk, reset, then send one content chunk
      with ``send_every_n_events=1`` and assert a flush fires for it.
    """
    handler = ChatCompletionTextHandler(replacers=[], send_every_n_events=1)
    received: list[TextFlushed] = []
    handler.text_bus.subscribe(received.append)

    await handler.on_chunk(_chunk(content="a"))
    assert len(received) == 1
    handler.reset()
    received.clear()

    await handler.on_chunk(_chunk(content="b"))
    assert len(received) == 1
    assert received[0].chunk_index == 0


class _TrailingFlushReplacer:
    """Replacer that buffers input until ``flush()``."""

    def __init__(self, trailing: str) -> None:
        self._trailing = trailing

    def process(self, text: str) -> str:
        return text

    def flush(self) -> str:
        out = self._trailing
        self._trailing = ""
        return out


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_text_handler__on_stream_end__does_not_publish_trailing_flush():
    """
    Purpose: ``on_stream_end`` must *not* publish a trailing :class:`TextFlushed`
      even when replacer residuals append to the accumulated text.
    Why this matters: :class:`StreamEnded` carries the authoritative final
      text. A trailing flush caused :class:`MessagePersistingSubscriber` to
      write the same full state twice (flush + end) against the SDK.
    Setup summary: Register a replacer that only surfaces its text on
      ``flush()``, drive one content chunk, call ``on_stream_end``, and
      assert no additional :class:`TextFlushed` was published while the
      handler's accumulated ``full_text`` still includes the residual.
    """
    replacer = _TrailingFlushReplacer(trailing="!")
    handler = ChatCompletionTextHandler(
        replacers=[replacer],  # type: ignore[list-item]
        send_every_n_events=1,
    )
    received: list[TextFlushed] = []
    handler.text_bus.subscribe(received.append)

    await handler.on_chunk(_chunk(content="hi"))
    assert len(received) == 1

    await handler.on_stream_end()

    assert len(received) == 1
    assert handler.get_text().full_text == "hi!"
