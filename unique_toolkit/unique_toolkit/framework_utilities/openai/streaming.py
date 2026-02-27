import logging
from datetime import datetime
from typing import Generic, Protocol, TypeVar

import httpx
import unique_sdk
from openai._streaming import AsyncStream
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
)
from pydantic import BaseModel
from unique_sdk import Message

from unique_toolkit import get_async_openai_client
from unique_toolkit.app.unique_settings import UniqueSettings

logger = logging.getLogger(__name__)

_T = TypeVar("_T", contravariant=True)


class ChatContextProtocol(
    Protocol
):  # TODO: Discuss this with team, we need to decide on context variables
    @property
    def chat_id(self) -> str: ...
    @property
    def assistant_message_id(self) -> str: ...


class ChatContext(BaseModel):
    chat_id: str
    assistant_message_id: str


class StreamPartHandler(Protocol, Generic[_T]):
    def handles_part(self, part: _T) -> bool: ...

    async def __call__(
        self,
        stream_part: _T,
        *,
        stream_part_index: int | None = None,
        send_every_n_events: int = 1,
    ) -> None: ...

    def on_stream_finished(self) -> None: ...


class CompletionChunkStreamPartHandler(StreamPartHandler[ChatCompletionChunk]):
    def __init__(
        self,
        chat_context: ChatContextProtocol,
        unique_settings: UniqueSettings,
    ):
        self._chat_context = chat_context
        self._full_text = ""
        self._unique_settings = unique_settings

    def handles_part(self, part: ChatCompletionChunk) -> bool:
        if isinstance(part, ChatCompletionChunk):
            return True
        return False

    def on_stream_finished(self) -> None:
        self._full_text = ""

    async def __call__(
        self,
        stream_part: ChatCompletionChunk,
        *,
        stream_part_index: int | None = None,
        send_every_n_events: int = 1,
    ) -> None:
        if len(stream_part.choices) == 0:
            return

        choice = stream_part.choices[0]
        self._full_text += choice.delta.content or ""

        if stream_part_index is not None:
            stream_part_index += 1

            if stream_part_index % send_every_n_events == 0:
                await unique_sdk.Message.create_event_async(
                    user_id=self._unique_settings.auth.user_id.get_secret_value(),
                    company_id=self._unique_settings.auth.company_id.get_secret_value(),
                    **unique_sdk.Message.CreateEventParams(
                        chatId=self._chat_context.chat_id,
                        messageId=self._chat_context.assistant_message_id,
                        text=self._full_text,
                    ),
                )
        else:
            await unique_sdk.Message.create_event_async(
                user_id=self._unique_settings.auth.user_id.get_secret_value(),
                company_id=self._unique_settings.auth.company_id.get_secret_value(),
                **unique_sdk.Message.CreateEventParams(
                    chatId=self._chat_context.chat_id,
                    messageId=self._chat_context.assistant_message_id,
                    text=self._full_text,
                ),
            )
        return


class ResponseStreamPartHandler(StreamPartHandler[ResponseStreamEvent]):
    def __init__(
        self, chat_context: ChatContextProtocol, unique_settings: UniqueSettings
    ):
        self._chat_context = chat_context
        self._full_text = ""
        self._unique_settings = unique_settings

    def handles_part(self, part: ResponseStreamEvent) -> bool:
        if isinstance(part, (ResponseTextDeltaEvent, ResponseCompletedEvent)):
            return True

        return False

    def on_stream_finished(self) -> None:
        self._full_text = ""

    async def __call__(
        self,
        stream_part: ResponseStreamEvent,
        *,
        stream_part_index: int | None = None,
        send_every_n_events: int = 1,
    ) -> None:
        if isinstance(stream_part, ResponseTextDeltaEvent):
            self._full_text += stream_part.delta

        if isinstance(stream_part, ResponseCompletedEvent):
            self._full_text = stream_part.response.output_text

        await unique_sdk.Message.create_event_async(
            user_id=self._unique_settings.auth.user_id.get_secret_value(),
            company_id=self._unique_settings.auth.company_id.get_secret_value(),
            **unique_sdk.Message.CreateEventParams(
                chatId=self._chat_context.chat_id,
                messageId=self._chat_context.assistant_message_id,
                text=self._full_text,
            ),
        )


async def stream_to_message(
    *,
    stream: AsyncStream[_T],
    stream_part_handler: list[StreamPartHandler[_T]],
    chat_context: ChatContextProtocol,
    settings: UniqueSettings | None = None,
    send_every_n_events: int = 1,
) -> Message:
    if settings is None:
        settings = UniqueSettings.from_env_auto_with_sdk_init()

    message = await unique_sdk.Message.modify_async(
        id=chat_context.assistant_message_id,
        chatId=chat_context.chat_id,
        user_id=settings.auth.user_id.get_secret_value(),
        company_id=settings.auth.company_id.get_secret_value(),
        startedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
    )

    stream_index = 0
    try:
        async for stream_part in stream:
            for handler in stream_part_handler:
                if handler.handles_part(stream_part):
                    await handler(
                        stream_part=stream_part,
                        stream_part_index=stream_index,
                        send_every_n_events=send_every_n_events,
                    )
            stream_index += 1
    except httpx.RemoteProtocolError as exc:
        logger.warning(
            "Stream connection closed prematurely (incomplete chunked read). "
            "Finalizing message with content received so far. Error: %s",
            exc,
        )

    # TODO: Fix api behavior and uncomment this
    # final_message = await unique_sdk.Message.modify_async(
    #    id=chat_context.assistant_message_id,
    #    chatId=chat_context.chat_id,
    #    user_id=settings.auth.user_id.get_secret_value(),
    #    company_id=settings.auth.company_id.get_secret_value(),
    #    stoppedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
    # )

    for handler in stream_part_handler:
        handler.on_stream_finished()

    return message


if __name__ == "__main__":
    import asyncio

    from unique_toolkit import LanguageModelName
    from unique_toolkit.app.dev_util import get_event_generator
    from unique_toolkit.app.schemas import ChatEvent

    async def main():
        settings = UniqueSettings.from_env_auto_with_sdk_init()
        for event in get_event_generator(
            unique_settings=settings, event_type=ChatEvent
        ):
            # Initialize services from event
            client = get_async_openai_client()

            # Example with the completion API
            # messages = (
            #    OpenAIMessageBuilder()
            #    .system_message_append(content="You are a helpful assistant")
            #    .user_message_append(content=event.payload.user_message.text)
            #    .messages
            # )

            # response = await client.chat.completions.create(
            #    model=LanguageModelName.AZURE_GPT_5_2025_0807,
            #    messages=messages,
            #    stream=True,
            # )

            # stream_part_handler = CompletionChunkStreamPartHandler(
            #    chat_context=ChatContext(
            #        chat_id=event.payload.chat_id,
            #        assistant_message_id=event.payload.assistant_message.id,
            #    ),
            #    unique_settings=settings,
            # )

            # await stream_to_message(
            #    chat_context=ChatContext(
            #        chat_id=event.payload.chat_id,
            #        assistant_message_id=event.payload.assistant_message.id,
            #    ),
            #    stream=response,
            #    stream_part_handler=[stream_part_handler],
            #    send_every_n_events=5,
            # )

            # Example with the responses API
            response = await client.responses.create(
                model=LanguageModelName.AZURE_GPT_5_2025_0807,
                input="Explain BPE encoding",
                stream=True,
            )

            stream_part_handler = ResponseStreamPartHandler(
                chat_context=ChatContext(
                    chat_id=event.payload.chat_id,
                    assistant_message_id=event.payload.assistant_message.id,
                ),
                unique_settings=settings,
            )

            await stream_to_message(
                chat_context=ChatContext(
                    chat_id=event.payload.chat_id,
                    assistant_message_id=event.payload.assistant_message.id,
                ),
                stream=response,
                stream_part_handler=[stream_part_handler],
                send_every_n_events=5,
            )

    asyncio.run(main())
