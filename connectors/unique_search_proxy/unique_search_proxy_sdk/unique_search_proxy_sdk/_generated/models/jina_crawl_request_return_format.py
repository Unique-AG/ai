from enum import StrEnum


class JinaCrawlRequestReturnFormat(StrEnum):
    HTML = "html"
    MARKDOWN = "markdown"
    PAGESHOT = "pageshot"
    SCREENSHOT = "screenshot"
    TEXT = "text"

    def __str__(self) -> str:
        return str(self.value)
