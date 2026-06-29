from enum import Enum


class BraveSearchRequestBraveSafeSearch(str, Enum):
    MODERATE = "moderate"
    OFF = "off"
    STRICT = "strict"

    def __str__(self) -> str:
        return str(self.value)
