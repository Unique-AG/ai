from enum import Enum


class GoogleSearchRequestSiteSearchFilter(str, Enum):
    E = "e"
    I = "i"

    def __str__(self) -> str:
        return str(self.value)
