from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
    LanguageModelName,

)

from unique_toolkit.framework_utilities.openai.client import get_async_openai_client
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
from datetime import datetime, timedelta
import unique_sdk

long_text = """
The story of the universe is a long and complex one. 
It is a story of the creation of the universe, the evolution of the universe, 
and the eventual destruction of the universe.
It all began with the big bang. A massive explosion that created the universe.
The big bang was not the beginning of the universe where the cosmic soup was created.
From the soup of the universe, the first atoms were formed. In particular hydrogen and helium.
The first stars were formed. These stars were the first galaxies.
The first galaxies were the first galaxies.
"""

   
from openai import AsyncOpenAI
from unique_toolkit.framework_utilities.openai import OpenAIMessageBuilder
from openai._streaming import AsyncStream
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from typing import Any, TypeVar, Callable, Protocol, Generic

_T = TypeVar("_T")

class StreamPartHandler(Protocol, Generic[_T]):

    
    @property
    def stream_part_type(self) -> type[_T]: ...

    async def __call__(
        self,
        stream_part: _T,
        *,
        stream_part_index: int | None = None,
        send_every_n_events: int = 1,
    ) -> None: ...


class CompletionChunkStreamPartHandler(StreamPartHandler[ChatCompletionChunk]):

    def __init__(
        self,
        user_id: str,
        company_id: str,
        chat_id: str,
        assistant_message_id: str,
    ):
        self._user_id = user_id
        self._company_id = company_id
        self._chat_id = chat_id
        self._assistant_message_id = assistant_message_id
        
        self._full_text = ""
    
    @property
    def stream_part_type(self) -> type[ChatCompletionChunk]:
        return ChatCompletionChunk
    
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
                   user_id=self._user_id,
                   company_id=self._company_id,
                   **unique_sdk.Message.CreateEventParams(
                       chatId=self._chat_id,
                       messageId=self._assistant_message_id,
                       text=self._full_text,
                   )
                )
        else:
            await unique_sdk.Message.create_event_async(
                user_id=self._user_id,
                company_id=self._company_id,
                **unique_sdk.Message.CreateEventParams(
                    chatId=self._chat_id,
                    messageId=self._assistant_message_id,
                    text=self._full_text,
                )
            )
        return


async def stream_to_message(
    *,
    company_id: str,
    user_id: str,
    chat_id: str,
    assistant_message_id: str,
    stream: AsyncStream[_T],
    stream_part_handler: list[StreamPartHandler[_T]],
    send_every_n_events: int = 1,

) -> None:
    
    await unique_sdk.Message.modify_async(
            id=assistant_message_id,
            chatId=chat_id,
            user_id=user_id,
            company_id=company_id,
            startedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
    
    stream_index = 0
    async for stream_part in stream:
        for handler in stream_part_handler:
            if handler.stream_part_type == type(stream_part):
                await handler(
                stream_part=stream_part, 
                stream_part_index=stream_index, 
                send_every_n_events=send_every_n_events
            )
        stream_index += 1
        
    await unique_sdk.Message.modify_async(
        id=assistant_message_id,
        chatId=chat_id,
        user_id=user_id,
        company_id=company_id,
        stoppedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    )
async def main():
    settings = UniqueSettings.from_env_auto_with_sdk_init()
    for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
        # Initialize services from event
        client = get_async_openai_client()
        messages = (
            OpenAIMessageBuilder()
            .system_message_append(content="You are a helpful assistant")
            .user_message_append(content=event.payload.user_message.text)
            .messages
        )

        
        t = await client.responses.create(
            model=LanguageModelName.AZURE_GPT_5_2025_0807,
            instructions="You are a helpful assistant.",
            input="Explain BPE encoding",
            stream=True,
            tools=[
                {"type": "code_interpreter", "container": {"type": "auto"}}
            ],
        )
        response = await client.chat.completions.create(
            model=LanguageModelName.AZURE_GPT_5_2025_0807,
            messages=messages,
            stream=True,
        )

        stream_part_handler = CompletionChunkStreamPartHandler(
            user_id=event.user_id,
            company_id=event.company_id,
            chat_id=event.payload.chat_id,
            assistant_message_id=event.payload.assistant_message.id,
        )

        await stream_to_message(
            company_id=event.company_id,
            user_id=event.user_id,
            chat_id=event.payload.chat_id,
            assistant_message_id=event.payload.assistant_message.id,
            stream=response,
            stream_part_handler=stream_part_handler,
            send_every_n_events=5,
        )

        

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())