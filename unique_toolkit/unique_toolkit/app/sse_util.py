import asyncio
import json
from logging import getLogger
from typing import Awaitable, Callable, Literal, overload

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
    headers = {
        "Authorization": f"Bearer {unique_settings.app.key.get_secret_value()}",
        "x-app-id": unique_settings.app.id.get_secret_value(),
        "x-company-id": unique_settings.auth.company_id.get_secret_value(),
    }
    return SSEClient(url=unique_settings.api.sse_url(subscriptions), headers=headers)


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
    try:
        event = json.loads(event.data)
    except Exception as e:
        LOGGER.error(f"Could not parse event data as JSON: {e}")
        return None

    match event_type:
        case EventName.EXTERNAL_MODULE_CHOSEN:
            return ChatEvent.model_validate(event)
        case EventName.BASE_EVENT:
            return BaseEvent.model_validate(event)

    return None


def run_demo_with_sse_client(
    unique_settings: UniqueSettings,
    handler: Callable[[ChatEvent | BaseEvent], Awaitable[None] | None],
    event_type: EventName,
) -> None:
    """
    Run a demo with an SSE client using sync handler.

    Args:
        unique_settings: The unique settings to use for the SSE client
        handler: The sync handler to use for the SSE client
        event_type: The type of event to use for the SSE client
    """
    subscription = event_type.value
    init_unique_sdk(unique_settings=unique_settings)

    for sse_event in get_sse_client(unique_settings, [subscription]):
        event = load_and_filter_event(sse_event, event_type)

        if event is None:
            continue

        if asyncio.iscoroutinefunction(handler):
            asyncio.run(handler(event))
        else:
            handler(event)
