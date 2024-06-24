from typing import Any, ClassVar, Dict, Literal

from unique_sdk._api_resource import APIResource


class Event(APIResource["Event"]):
    OBJECT_NAME: ClassVar[Literal["event"]] = "event"

    event: Literal[
        "unique.chat.user-message.created", "unique.chat.external-module.chosen"
    ]
    version: Literal["1.0.0"]
    createdAt: int
    payload: Dict[str, Any]
