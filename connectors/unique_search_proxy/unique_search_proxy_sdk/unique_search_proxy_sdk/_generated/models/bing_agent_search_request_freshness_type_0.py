from enum import StrEnum


class BingAgentSearchRequestFreshnessType0(StrEnum):
    DAY = "Day"
    MONTH = "Month"
    WEEK = "Week"

    def __str__(self) -> str:
        return str(self.value)
