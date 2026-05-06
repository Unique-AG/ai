from typing import Any, Literal

from unique_sdk._api_resource import APIResource
from unique_sdk._util import classproperty


class Event(APIResource["Event"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["event"]:
        return "event"

    event: Literal[
        "unique.chat.user-message.created", "unique.chat.external-module.chosen"
    ]
    version: Literal["1.0.0"]
    createdAt: int
    payload: dict[str, Any]
