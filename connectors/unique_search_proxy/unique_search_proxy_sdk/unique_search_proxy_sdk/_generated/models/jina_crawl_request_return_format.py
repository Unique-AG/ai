from enum import Enum


class JinaCrawlRequestReturnFormat(str, Enum):
    HTML = "html"
    MARKDOWN = "markdown"
    PAGESHOT = "pageshot"
    SCREENSHOT = "screenshot"
    TEXT = "text"

    def __str__(self) -> str:
        return str(self.value)
