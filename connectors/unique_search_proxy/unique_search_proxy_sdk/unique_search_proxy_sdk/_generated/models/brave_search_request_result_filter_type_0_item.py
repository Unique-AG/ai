from enum import StrEnum


class BraveSearchRequestResultFilterType0Item(StrEnum):
    DISCUSSIONS = "discussions"
    FAQ = "faq"
    INFOBOX = "infobox"
    LOCATIONS = "locations"
    NEWS = "news"
    QUERY = "query"
    SUMMARIZER = "summarizer"
    VIDEOS = "videos"
    WEB = "web"

    def __str__(self) -> str:
        return str(self.value)
