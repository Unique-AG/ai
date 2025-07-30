import asyncio
import json
from enum import StrEnum
from pathlib import Path
from typing import Awaitable, Callable, Literal, overload

from unique_toolkit.app import BaseEvent, ChatEvent, EventName
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.sse_util import run_demo_with_sse_client
from unique_toolkit.app.unique_settings import UniqueSettings


@overload
def load_event(
    file_path: Path, event_type: Literal[EventName.EXTERNAL_MODULE_CHOSEN]
) -> ChatEvent: ...


@overload
def load_event(
    file_path: Path, event_type: Literal[EventName.BASE_EVENT]
) -> BaseEvent: ...


@overload
def load_event(
    file_path: Path, event_type: EventName
) -> ChatEvent | BaseEvent | None: ...


def load_event(file_path: Path, event_type: EventName) -> ChatEvent | BaseEvent | None:
    with file_path.open("r") as file:
        event = json.load(file)

    match event_type:
        case EventName.EXTERNAL_MODULE_CHOSEN:
            return ChatEvent.model_validate(event)
        case EventName.BASE_EVENT:
            return BaseEvent.model_validate(event)


def run_demo_with_with_saved_event(
    unique_settings: UniqueSettings,
    handler: Callable[[ChatEvent | BaseEvent], Awaitable[None] | None],
    event_type: EventName,
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
    event = load_event(file_path, event_type)

    if event is None:
        raise ValueError(f"Event not found in {file_path}")

    if asyncio.iscoroutinefunction(handler):
        asyncio.run(handler(event))
    else:
        handler(event)


class DevMode(StrEnum):
    SSE = "sse"
    FILE = "file"


def run_dev(
    process_event: Callable[[ChatEvent | BaseEvent], Awaitable[None] | None],
    event_type: EventName,
    unique_settings: UniqueSettings,
    mode: DevMode = DevMode.SSE,
    file_path: Path | None = None,
) -> None:
    """
    Run a demo with an SSE client or a saved event.

    Args:
        process_event: The function to process the event
        event_type: The type of event to process
        unique_settings: The unique settings to use for the SSE client
        mode: The mode to run the demo in
        file_path: The path to the file to load the event from

    Note: process event input must match with event_type.
    """
    match mode:
        case DevMode.SSE:
            run_demo_with_sse_client(
                unique_settings=unique_settings,
                handler=process_event,
                event_type=event_type,
            )
        case DevMode.FILE:
            if file_path is None:
                raise ValueError("file_path is required when mode is FILE")

            run_demo_with_with_saved_event(
                unique_settings=unique_settings,
                handler=process_event,
                event_type=event_type,
                file_path=file_path,
            )
