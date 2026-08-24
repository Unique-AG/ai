from enum import Enum


class BingAgentSearchRequestFreshnessType0(str, Enum):
    DAY = "Day"
    MONTH = "Month"
    WEEK = "Week"

    def __str__(self) -> str:
        return str(self.value)
