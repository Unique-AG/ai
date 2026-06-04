from enum import Enum


class GoogleRequestSiteSearchFilterType0(str, Enum):
    E = "e"
    I = "i"

    def __str__(self) -> str:
        return str(self.value)
