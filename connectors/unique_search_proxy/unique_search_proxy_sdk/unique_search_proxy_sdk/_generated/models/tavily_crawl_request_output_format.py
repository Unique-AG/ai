from enum import Enum


class TavilyCrawlRequestOutputFormat(str, Enum):
    MARKDOWN = "markdown"
    TEXT = "text"

    def __str__(self) -> str:
        return str(self.value)
