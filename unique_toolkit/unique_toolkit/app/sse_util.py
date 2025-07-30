import json
from logging import getLogger
from typing import Callable, Literal, overload

from sseclient import Event as SSEEvent
from sseclient import SSEClient

from unique_toolkit.app import BaseEvent, ChatEvent, EventName
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.unique_settings import UniqueSettings

LOGGER = getLogger(__name__)


def get_sse_client(
    unique_settings: UniqueSettings,
    subscriptions: list[str],
) -> SSEClient:
    url = f"{unique_settings.api.base_url}/public/event-socket/events/stream?subscriptions={','.join(subscriptions)}"
    headers = {
        "Authorization": f"Bearer {unique_settings.app.key.get_secret_value()}",
        "x-app-id": unique_settings.app.id.get_secret_value(),
        "x-company-id": unique_settings.auth.company_id.get_secret_value(),
    }
    return SSEClient(url=url, headers=headers)


@overload
def load_and_filter_event(
    event: SSEEvent,
    event_type: Literal[EventName.EXTERNAL_MODULE_CHOSEN],
) -> ChatEvent | None: ...


@overload
def load_and_filter_event(
    event: SSEEvent,
    event_type: Literal[EventName.BASE_EVENT],
) -> BaseEvent | None: ...


@overload
def load_and_filter_event(
    event: SSEEvent,
    event_type: EventName,
) -> ChatEvent | BaseEvent | None: ...


def load_and_filter_event(
    event: SSEEvent,
    event_type: EventName,
) -> ChatEvent | BaseEvent | None:
    event = json.loads(event.data)

    match event_type:
        case EventName.EXTERNAL_MODULE_CHOSEN:
            return ChatEvent.model_validate(event)
        case EventName.BASE_EVENT:
            return BaseEvent.model_validate(event)

    return None


def execute_event_handler(
    handler: Callable[[ChatEvent | BaseEvent], None],
    sse_event: SSEEvent,
    event_type: EventName,
) -> None:
    """
    Execute a handler function that expects an Event.
    The event type is determined by the event_type parameter
    and must match to the event expected by the handler.

    Args:
        handler: A callable that takes ChatEvent as its parameter
        sse_event: The SSE event to convert and pass to the handler
        event_type: The type of event expected by the handler
    Raises:
        TypeError: If the event cannot be converted to the expected type
    """
    event = load_and_filter_event(sse_event, event_type)

    if event is None:
        raise TypeError("Could not convert SSE event to ChatEvent")
    handler(event)


def run_demo_with_sse_client(
    unique_settings: UniqueSettings,
    handler: Callable[[ChatEvent | BaseEvent], None],
    event_type: EventName,
) -> None:
    """
    Run a demo with an SSE client.

    Note: event_type is the type of event that the handler expects.

    Args:
        unique_settings: The unique settings to use for the SSE client
        handler: The handler to use for the SSE client
        event_type: The type of event to use for the SSE client
    """
    subscription = event_type.value
    init_unique_sdk(unique_settings=unique_settings)
    sse_client = get_sse_client(unique_settings, [subscription])
    for event in sse_client:
        execute_event_handler(handler, event, event_type)
