from enum import StrEnum


class FirecrawlSearchRequestSources(StrEnum):
    NEWS = "news"
    WEB = "web"
    WEB_AND_NEWS = "web_and_news"

    def __str__(self) -> str:
        return str(self.value)
