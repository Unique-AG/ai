from enum import Enum


class GoogleSearchRequestSiteSearchFilterType0(str, Enum):
    E = "e"
    I = "i"

    def __str__(self) -> str:
        return str(self.value)
