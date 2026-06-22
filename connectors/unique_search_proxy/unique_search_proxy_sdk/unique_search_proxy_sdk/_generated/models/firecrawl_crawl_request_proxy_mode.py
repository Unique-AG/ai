from enum import Enum


class FirecrawlCrawlRequestProxyMode(str, Enum):
    AUTO = "auto"
    BASIC = "basic"
    ENHANCED = "enhanced"

    def __str__(self) -> str:
        return str(self.value)
