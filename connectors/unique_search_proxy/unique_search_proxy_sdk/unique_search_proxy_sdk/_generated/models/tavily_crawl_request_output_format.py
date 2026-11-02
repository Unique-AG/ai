from enum import StrEnum


class TavilyCrawlRequestOutputFormat(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"

    def __str__(self) -> str:
        return str(self.value)
