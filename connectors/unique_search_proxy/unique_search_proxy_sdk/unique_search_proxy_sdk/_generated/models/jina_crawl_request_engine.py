from enum import StrEnum


class JinaCrawlRequestEngine(StrEnum):
    AUTO = "auto"
    BROWSER = "browser"
    CF_BROWSER_RENDERING = "cf-browser-rendering"
    DIRECT = "direct"

    def __str__(self) -> str:
        return str(self.value)
