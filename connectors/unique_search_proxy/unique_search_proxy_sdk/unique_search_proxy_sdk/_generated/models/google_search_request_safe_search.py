from enum import Enum


class GoogleSearchRequestSafeSearch(str, Enum):
    ACTIVE = "active"
    OFF = "off"

    def __str__(self) -> str:
        return str(self.value)
