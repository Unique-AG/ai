from enum import StrEnum


class FirecrawlSearchRequestCategoryType0(StrEnum):
    DEVELOPER = "developer"
    GOV = "gov"
    PDF = "pdf"
    RESEARCH = "research"

    def __str__(self) -> str:
        return str(self.value)
