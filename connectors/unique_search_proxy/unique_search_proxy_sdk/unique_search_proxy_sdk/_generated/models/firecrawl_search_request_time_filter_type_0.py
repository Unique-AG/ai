from enum import StrEnum


class FirecrawlSearchRequestTimeFilterType0(StrEnum):
    QDRD = "qdr:d"
    QDRH = "qdr:h"
    QDRM = "qdr:m"
    QDRW = "qdr:w"
    QDRY = "qdr:y"

    def __str__(self) -> str:
        return str(self.value)
