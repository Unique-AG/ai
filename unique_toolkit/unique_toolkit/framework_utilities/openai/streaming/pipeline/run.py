"""Run a typed stream through an accumulator and optional persistence layer."""

from __future__ import annotations

from collections.abc import AsyncIterable
from datetime import datetime, timezone
from typing import TypeVar

from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.responses import ResponseStreamEvent

from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

from .protocols import (
    ResponsesStreamAccumulatorProtocol,
    ResponseStreamPersistenceProtocol,
    StreamAccumulatorProtocol,
    StreamPersistenceProtocol,
)

TStreamEvent = TypeVar("TStreamEvent")
TStreamResult = TypeVar("TStreamResult")


async def run_stream_pipeline(
    stream: AsyncIterable[TStreamEvent],
    *,
    accumulator: StreamAccumulatorProtocol[TStreamEvent, TStreamResult],
    message_id: str,
    chat_id: str,
    created_at: datetime | None = None,
    persistence: StreamPersistenceProtocol[TStreamEvent] | None = None,
) -> TStreamResult:
    """Consume any async stream: fold → optional persistence → final result.

    The accumulator is updated **before** ``persistence.on_event`` so sinks can
    read consistent folded state if they hold a reference to the accumulator.

    Use :func:`run_responses_stream_pipeline` when streaming OpenAI
    :class:`~openai.types.responses.ResponseStreamEvent` into
    :class:`~unique_toolkit.language_model.schemas.LanguageModelStreamResponse`.

    **Lifecycle:** Calls ``reset()`` on the accumulator and on persistence (when
    provided) **before** consuming the stream, so sequential reuse of the same
    objects does not merge streams. Do **not** share one accumulator or persistence
    instance across **concurrent** runs — use one pair per concurrent task.
    """
    accumulator.reset()
    if persistence is not None:
        persistence.reset()

    index = 0
    async for event in stream:
        accumulator.apply(event)
        if persistence is not None:
            await persistence.on_event(event, index=index)
        index += 1

    if persistence is not None:
        await persistence.on_stream_end()

    ts = created_at if created_at is not None else datetime.now(timezone.utc)
    return accumulator.build_stream_result(
        message_id=message_id,
        chat_id=chat_id,
        created_at=ts,
    )


async def run_responses_stream_pipeline(
    stream: AsyncIterable[ResponseStreamEvent],
    *,
    accumulator: ResponsesStreamAccumulatorProtocol,
    message_id: str,
    chat_id: str,
    created_at: datetime | None = None,
    persistence: ResponseStreamPersistenceProtocol | None = None,
) -> LanguageModelStreamResponse:
    """Specialization of :func:`run_stream_pipeline` for OpenAI Responses streams."""
    return await run_stream_pipeline(
        stream,
        accumulator=accumulator,
        message_id=message_id,
        chat_id=chat_id,
        created_at=created_at,
        persistence=persistence,
    )


async def run_chat_completions_stream_pipeline(
    stream: AsyncIterable[ChatCompletionChunk],
    *,
    accumulator: StreamAccumulatorProtocol[
        ChatCompletionChunk, LanguageModelStreamResponse
    ],
    message_id: str,
    chat_id: str,
    created_at: datetime | None = None,
    persistence: StreamPersistenceProtocol[ChatCompletionChunk] | None = None,
) -> LanguageModelStreamResponse:
    """Specialization of :func:`run_stream_pipeline` for chat completion chunks."""
    return await run_stream_pipeline(
        stream,
        accumulator=accumulator,
        message_id=message_id,
        chat_id=chat_id,
        created_at=created_at,
        persistence=persistence,
    )
