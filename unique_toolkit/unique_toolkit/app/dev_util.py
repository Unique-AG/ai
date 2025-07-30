import json
from pathlib import Path
from typing import Callable, Literal, overload

from unique_toolkit.app import BaseEvent, ChatEvent, EventName
from unique_toolkit.app.init_sdk import init_unique_sdk
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
    handler: Callable[[ChatEvent | BaseEvent], None],
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

    handler(event)
