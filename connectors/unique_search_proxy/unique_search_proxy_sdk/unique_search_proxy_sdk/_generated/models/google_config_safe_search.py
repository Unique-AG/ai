from enum import Enum


class GoogleConfigSafeSearch(str, Enum):
    ACTIVE = "active"
    OFF = "off"

    def __str__(self) -> str:
        return str(self.value)
