from enum import Enum


class JinaCrawlRequestRetainImagesType0(str, Enum):
    ALL = "all"
    ALL_P = "all_p"
    ALT = "alt"
    ALT_P = "alt_p"
    NONE = "none"

    def __str__(self) -> str:
        return str(self.value)
