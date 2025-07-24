from unique_toolkit.app.unique_settings import UniqueSettings
import json
from typing import overload, Literal, Type
from unique_toolkit.app import EventName, ChatEvent
from logging import getLogger

LOGGER = getLogger(__name__)

@overload
def load_and_filter_event(
    event: dict, event_type: Literal[EventName.EXTERNAL_MODULE_CHOSEN]
) -> Type[ChatEvent] | None: ...


def load_and_filter_event(event: dict, event_type: EventName):
    event = json.loads(event.data)

    match event_type:
        case EventName.EXTERNAL_MODULE_CHOSEN:
            return ChatEvent(**event)

    return None
