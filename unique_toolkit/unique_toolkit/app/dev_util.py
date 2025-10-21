import asyncio
import json
from logging import getLogger
from pathlib import Path
from typing import (
    Awaitable,
    Callable,
    Generator,
    TypeVar,
)

from sseclient import SSEClient

from unique_toolkit._common.exception import ConfigurationException
from unique_toolkit.app import BaseEvent, ChatEvent, EventName
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.unique_settings import UniqueSettings

T = TypeVar("T", bound=BaseEvent)

LOGGER = getLogger(__name__)


def get_event_name_from_event_class(event_class: type[T]) -> EventName | None:
    if event_class is ChatEvent:
        return EventName.EXTERNAL_MODULE_CHOSEN

    return None


def get_sse_client(
    unique_settings: UniqueSettings,
    subscriptions: list[str],
) -> SSEClient:
    headers = {
        "Authorization": f"Bearer {unique_settings.app.key.get_secret_value()}",
        "x-app-id": unique_settings.app.id.get_secret_value(),
        "x-company-id": unique_settings.auth.company_id.get_secret_value(),
        "x-user-id": unique_settings.auth.user_id.get_secret_value(),
        "x-api-version": unique_settings.api.version,
    }
    return SSEClient(url=unique_settings.api.sse_url(subscriptions), headers=headers)


def get_event_generator(
    unique_settings: UniqueSettings,
    event_type: type[T],
) -> Generator[T, None, None]:
    """
    Generator that updates the unique settings according to the events and
    yields only events of the specified type from an SSE stream.

    Args:
        sse_client: The SSE client to read events from
        event_type: The event class type to filter for

    Yields:
        Events matching the specified type
    """
    event_name = get_event_name_from_event_class(event_type)
    if (
        event_name is None
        or not issubclass(event_type, BaseEvent)
        or event_type is BaseEvent
    ):
        raise ValueError(f"Event model {event_type} is not a valid event model")

    subscription = event_name.value

    for sse_event in get_sse_client(unique_settings, [subscription]):
        try:
            payload = json.loads(sse_event.data)
            parsed_event = event_type.model_validate(payload)
            if parsed_event is None or parsed_event.filter_event(
                filter_options=unique_settings.chat_event_filter_options
            ):
                continue

            unique_settings.update_from_event(event=parsed_event)

            yield parsed_event

        except ConfigurationException as e:
            # Re-raise ConfigurationException from filter_event (configuration errors)
            raise e
        except Exception as e:
            LOGGER.error(f"Could not parse SSE event data as JSON: {e}")
            continue


def get_event_stream(
    event_type: type[T] = BaseEvent,
    settings_config: UniqueSettings | str | None = None,
) -> Generator[T, None, None]:
    """
    Get an event stream from the SSE client.

    Args:
        event_type: The type of event to get
        settings_or_filename: The settings or filename to use to setup the Unique settings object
    """

    if isinstance(settings_config, str):
        unique_settings = UniqueSettings.from_env_auto_with_sdk_init(
            filename=settings_config
        )
    elif isinstance(settings_config, UniqueSettings):
        unique_settings = settings_config
    else:
        unique_settings = UniqueSettings.from_env_auto_with_sdk_init()

    return get_event_generator(unique_settings, event_type)


def run_demo_with_sse_client(
    unique_settings: UniqueSettings,
    handler: Callable[[BaseEvent], Awaitable[None] | None],
    event_type: type[BaseEvent],
) -> None:
    """
    Run a demo with an SSE client using sync handler.

    Args:
        unique_settings: The unique settings to use for the SSE client
        handler: The sync handler to use for the SSE client
        event_type: The type of event to use for the SSE client
    """

    event_name = get_event_name_from_event_class(event_type)
    if event_name is None:
        return

    init_unique_sdk(unique_settings=unique_settings)
    is_async_handler = asyncio.iscoroutinefunction(handler)

    for event in get_event_generator(unique_settings, event_type):
        if is_async_handler:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(handler(event))
        else:
            handler(event)


def load_event(file_path: Path, event_type: type[BaseEvent]) -> BaseEvent:
    with file_path.open("r") as file:
        event = json.load(file)

    return event_type.model_validate(event)


def run_demo_with_with_saved_event(
    unique_settings: UniqueSettings,
    handler: Callable[[BaseEvent], Awaitable[None] | None],
    event_type: type[BaseEvent],
    file_path: Path,
) -> None:
    """
    Run a demo with an SSE client.

    Note: event_type is the type of event that the handler expects.

    Args:
        unique_settings: The unique settings to use for the SSE client
        handler: The handler to use for the SSE client
        event_type: The type of event to use for the SSE client
    """
    init_unique_sdk(unique_settings=unique_settings)

    event_name = get_event_name_from_event_class(event_type)
    if event_name is None:
        return

    event = load_event(file_path, event_type)
    if event is None:
        raise ValueError(f"Event not found in {file_path}")

    if asyncio.iscoroutinefunction(handler):
        asyncio.run(handler(event))
    else:
        handler(event)
