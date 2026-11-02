from enum import StrEnum


class PerplexitySearchRequestSearchRecencyFilterType0(StrEnum):
    DAY = "day"
    HOUR = "hour"
    MONTH = "month"
    WEEK = "week"
    YEAR = "year"

    def __str__(self) -> str:
        return str(self.value)
