from enum import StrEnum


class FirecrawlSearchRequestZeroDataRetention(StrEnum):
    ANON = "anon"
    DEPLOYMENT = "deployment"
    ZDR = "zdr"

    def __str__(self) -> str:
        return str(self.value)
