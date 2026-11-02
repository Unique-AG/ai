from enum import StrEnum


class GoogleSearchRequestSafeSearch(StrEnum):
    ACTIVE = "active"
    OFF = "off"

    def __str__(self) -> str:
        return str(self.value)
