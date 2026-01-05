import asyncio
import inspect
from collections import defaultdict
from collections.abc import Coroutine
from typing import (
    Any,
    AsyncIterable,
    Callable,
    Protocol,
    TypedDict,
    TypeVar,
    cast,
    get_args,
)

from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
)
from unique_toolkit import (
    ChatService,
    LanguageModelName,
)
from unique_toolkit.app import ChatEvent
from unique_toolkit.content import ContentReference

# ---------- Responses API Specific ----------

EventType = TypeVar("EventType", bound=ResponseStreamEvent, contravariant=True)


ResponsesApiEventSubscriber = (
    Callable[[EventType], Coroutine[Any, Any, None]]
    | Callable[[EventType], None]
)


class ResponsesAPIEventDispatcher:
    """
    The Responses API sends events back in the stream.
    This class gathers and dispatches events to a list of subscribers for each event type.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[ResponsesApiEventSubscriber]] = (
            defaultdict(list)
        )

    def subscribe(
        self,
        subscriber: ResponsesApiEventSubscriber[EventType],
        *event_types: type[EventType],
    ) -> None:
        for event_type in event_types:
            event_name = get_args(event_type.model_fields["type"].annotation)[
                0
            ]
            self._subscribers[event_name].append(subscriber)

    async def handle_stream(
        self, stream: AsyncIterable[ResponseStreamEvent]
    ) -> list[ResponseStreamEvent]:
        events = []

        async for event in stream:
            events.append(event)

            tasks = []
            for subscriber in self._subscribers[event.type]:
                res = subscriber(event)
                if inspect.isawaitable(res):
                    tasks.append(asyncio.create_task(res))

            # Potentially handle errors here
            # Subscribers should not block for too long otherwise stream processing would be slow
            await asyncio.gather(*tasks)

        return events


# ---------- General ----------
# Define a streaming processor (which will subscribe to the event dispatcher)
# Goal is to handle what is written to the chat


class MessageUpdateParams(TypedDict, total=False): # TypedDict can be replaced
    text: str
    references: list[ContentReference]
    debug_info: dict[str, Any]


class SyncStreamingProcessor(Protocol):
    """
    A streaming processor that instantly returns an update, e.g referencing processor
    """

    def __call__(
        self,
        original_text: str,
        text: str,
        text_delta: str,
        references: list[ContentReference],
        debug_info: dict[str, Any],
    ) -> MessageUpdateParams: ...


class CallbackStreamingProcessor(Protocol):
    """
    A streaming processor that can return a coroutine that will scheduled in the background. Example: fetch and upload a file to the KB.
    The callback is called once the coroutine finishes.
    """

    def __call__(
        self,
        original_text: str,
        text: str,
        text_delta: str,
        references: list[ContentReference],
        debug_info: dict[str, Any],
    ) -> tuple[MessageUpdateParams, Coroutine[Any, Any, None]]: ...

    def callback(
        self,
        text: str,
        references: list[ContentReference],
        debug_info: dict[str, Any],
    ) -> MessageUpdateParams: ...


StreamingProcessor = SyncStreamingProcessor | CallbackStreamingProcessor


class StreamingHandler:
    def __init__(
        self,
        chat_service: ChatService,
        processors: list[StreamingProcessor],
    ) -> None:
        self._chat_service = chat_service

        self._processors: list[StreamingProcessor] = processors
        self._text = ""
        self._original_text = ""
        self._references = []
        self._debug_info = {}

        self._bg_tasks = []

    async def _save_message(self) -> None:
        await asyncio.gather(*self._bg_tasks)

        await self._chat_service.modify_assistant_message_async(
            content=self._text,
            original_content=self._original_text,
            references=self._references,
            debug_info=self._debug_info,
        )

    async def _create_message_event(self) -> None:
        await self._chat_service.modify_assistant_message_async(  # TODO: Replace with message event
            content=self._text,
            original_content=self._original_text,
            references=self._references,
            debug_info=self._debug_info,
        )

    def _update_message(self, update_params: MessageUpdateParams) -> None:
        if "text" in update_params:
            self._text = update_params["text"]
        if "references" in update_params:
            self._references = update_params["references"]
        if "debug_info" in update_params:
            self._debug_info = update_params["debug_info"]

    async def _callback(
        self,
        processor: CallbackStreamingProcessor,
        coro: Coroutine[Any, Any, None],
    ) -> None:
        await coro
        update_params = processor.callback(
            text=self._text,
            references=self._references,
            debug_info=self._debug_info,
        )
        self._update_message(update_params)
        await self._create_message_event()

    def _handle_processor(
        self, processor: StreamingProcessor, event: ResponseTextDeltaEvent
    ) -> MessageUpdateParams:
        result = processor(
            original_text=self._original_text,
            text=self._text,
            text_delta=event.delta,
            references=self._references,
            debug_info=self._debug_info,
        )

        if isinstance(result, tuple):
            update_params, callback = result
            processor = cast(CallbackStreamingProcessor, processor)
            self._bg_tasks.append(
                asyncio.create_task(self._callback(processor, callback))
            )
        else:
            update_params = result

        return update_params

    async def __call__(
        self, event: ResponseCompletedEvent | ResponseTextDeltaEvent
    ) -> None:
        if isinstance(event, ResponseCompletedEvent):
            await self._save_message()

        elif isinstance(event, ResponseTextDeltaEvent):
            self._text += event.delta
            self._original_text += event.delta

            for processor in self._processors:
                update_params = self._handle_processor(processor, event)
                self._update_message(update_params)
            await self._create_message_event()


if __name__ == "__main__":
    import unique_sdk
    from unique_toolkit.framework_utilities.openai.client import (
        get_async_openai_client,
    )

    unique_sdk.api_key = "dummy"
    unique_sdk.app_id = "dummy"
    unique_sdk.api_base = "http://localhost:8092/public"

    async def main():
        client = get_async_openai_client()

        response = await client.responses.create(
            model=LanguageModelName.AZURE_GPT_5_2025_0807,
            instructions="You are a helpful assistant.",
            input="Explain BPE encoding",
            stream=True,
            tools=[
                {"type": "code_interpreter", "container": {"type": "auto"}}
            ],
        )

        dispatcher = ResponsesAPIEventDispatcher()

        with open("event.json", "r") as f:
            event = ChatEvent.model_validate_json(f.read())

        chat_service = ChatService(event)

        stream_handler = StreamingHandler(
            chat_service=chat_service, processors=[]
        )

        dispatcher.subscribe(
            stream_handler, ResponseTextDeltaEvent, ResponseCompletedEvent
        )

        await dispatcher.handle_stream(response)

    asyncio.run(main())
