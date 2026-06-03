from enum import Enum


class ContentTypeHandlerPolicy(str, Enum):
    ALLOW = "allow"
    FORBID = "forbid"

    def __str__(self) -> str:
        return str(self.value)
