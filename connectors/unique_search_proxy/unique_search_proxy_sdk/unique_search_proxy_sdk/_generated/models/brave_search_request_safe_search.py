from enum import StrEnum


class BraveSearchRequestSafeSearch(StrEnum):
    MODERATE = "moderate"
    OFF = "off"
    STRICT = "strict"

    def __str__(self) -> str:
        return str(self.value)
