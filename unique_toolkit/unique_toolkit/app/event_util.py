import json
from logging import getLogger
from typing import Literal, overload

from unique_toolkit.app import ChatEvent, EventName

LOGGER = getLogger(__name__)


@overload
def load_and_filter_event(
    event: dict,
    event_type: Literal[EventName.EXTERNAL_MODULE_CHOSEN],
) -> type[ChatEvent] | None: ...


def load_and_filter_event(event: dict, event_type: EventName):
    event = json.loads(event.data)

    match event_type:
        case EventName.EXTERNAL_MODULE_CHOSEN:
            return ChatEvent(**event)

    return None
