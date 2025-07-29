import json
from logging import getLogger
from typing import Literal, overload

from sseclient import Event as SSEEvent

from unique_toolkit.app import ChatEvent, EventName

LOGGER = getLogger(__name__)


@overload
def load_and_filter_event(
    event: SSEEvent,
    event_type: Literal[EventName.EXTERNAL_MODULE_CHOSEN],
) -> ChatEvent | None: ...


def load_and_filter_event(event: SSEEvent, event_type: EventName):
    event = json.loads(event.data)

    match event_type:
        case EventName.EXTERNAL_MODULE_CHOSEN:
            return ChatEvent.model_validate(event)

    return None
