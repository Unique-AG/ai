from enum import StrEnum


class FirecrawlCrawlRequestProxyMode(StrEnum):
    AUTO = "auto"
    BASIC = "basic"
    ENHANCED = "enhanced"

    def __str__(self) -> str:
        return str(self.value)
