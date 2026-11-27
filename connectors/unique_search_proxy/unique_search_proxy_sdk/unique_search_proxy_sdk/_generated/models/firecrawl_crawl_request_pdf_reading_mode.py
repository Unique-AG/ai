from enum import StrEnum


class FirecrawlCrawlRequestPDFReadingMode(StrEnum):
    AUTO = "auto"
    FAST = "fast"
    OCR = "ocr"

    def __str__(self) -> str:
        return str(self.value)
