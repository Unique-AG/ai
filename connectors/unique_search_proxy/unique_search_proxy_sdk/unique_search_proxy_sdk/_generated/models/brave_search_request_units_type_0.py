from enum import StrEnum


class BraveSearchRequestUnitsType0(StrEnum):
    IMPERIAL = "imperial"
    METRIC = "metric"

    def __str__(self) -> str:
        return str(self.value)
