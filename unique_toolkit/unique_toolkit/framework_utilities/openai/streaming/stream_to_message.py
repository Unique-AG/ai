"""Bridge OpenAI streaming APIs to the Unique SDK using the streaming pipeline."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence
from datetime import datetime, timezone

import httpx
import unique_sdk
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.responses import ResponseStreamEvent
from unique_sdk import Message

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline import (
    ChatCompletionSdkPersistence,
    ChatCompletionStreamAccumulator,
    ResponsesSdkPersistence,
    ResponsesStreamAccumulator,
    run_chat_completions_stream_pipeline,
    run_responses_stream_pipeline,
)

_LOGGER = logging.getLogger(__name__)


async def stream_responses_to_message(
    *,
    stream: AsyncIterator[ResponseStreamEvent],
    settings: UniqueSettings | None = None,
    replacers: Sequence[StreamingReplacerProtocol] | None = None,
) -> Message:
    """Stream an OpenAI Responses ``AsyncIterator`` to the Unique SDK (pipeline + SDK persistence)."""
    if settings is None:
        settings = UniqueSettings.from_env_auto_with_sdk_init()
    if settings.context.chat is None:
        raise ValueError("Chat context is not set")

    message = await unique_sdk.Message.modify_async(
        id=settings.context.chat.last_assistant_message_id,
        chatId=settings.context.chat.chat_id,
        user_id=settings.context.auth.user_id.get_secret_value(),
        company_id=settings.context.auth.company_id.get_secret_value(),
        startedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
    )

    chat = settings.context.chat
    accumulator = ResponsesStreamAccumulator()
    persistence = ResponsesSdkPersistence(
        settings,
        replacers=list(replacers or []),
    )

    try:
        await run_responses_stream_pipeline(
            stream,
            accumulator=accumulator,
            persistence=persistence,
            message_id=chat.last_assistant_message_id,
            chat_id=chat.chat_id,
            created_at=datetime.now(timezone.utc),
        )
    except httpx.RemoteProtocolError as exc:
        _LOGGER.warning(
            "Stream connection closed prematurely (incomplete chunked read). "
            "Finalizing message with content received so far. Error: %s",
            exc,
        )

    return message


async def stream_chat_completions_to_message(
    *,
    stream: AsyncIterator[ChatCompletionChunk],
    settings: UniqueSettings | None = None,
    replacers: Sequence[StreamingReplacerProtocol] | None = None,
    send_every_n_events: int = 1,
) -> Message:
    """Stream chat completion chunks to the Unique SDK (pipeline + SDK persistence)."""
    if settings is None:
        settings = UniqueSettings.from_env_auto_with_sdk_init()
    if settings.context.chat is None:
        raise ValueError("Chat context is not set")

    message = await unique_sdk.Message.modify_async(
        id=settings.context.chat.last_assistant_message_id,
        chatId=settings.context.chat.chat_id,
        user_id=settings.context.auth.user_id.get_secret_value(),
        company_id=settings.context.auth.company_id.get_secret_value(),
        startedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
    )

    chat = settings.context.chat
    accumulator = ChatCompletionStreamAccumulator()
    persistence = ChatCompletionSdkPersistence(
        settings,
        replacers=list(replacers or []),
        send_every_n_events=send_every_n_events,
    )

    try:
        await run_chat_completions_stream_pipeline(
            stream,
            accumulator=accumulator,
            persistence=persistence,
            message_id=chat.last_assistant_message_id,
            chat_id=chat.chat_id,
            created_at=datetime.now(timezone.utc),
        )
    except httpx.RemoteProtocolError as exc:
        _LOGGER.warning(
            "Stream connection closed prematurely (incomplete chunked read). "
            "Finalizing message with content received so far. Error: %s",
            exc,
        )

    return message
