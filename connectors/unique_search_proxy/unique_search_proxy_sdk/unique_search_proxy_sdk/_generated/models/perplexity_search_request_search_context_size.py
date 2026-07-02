from enum import Enum


class PerplexitySearchRequestSearchContextSize(str, Enum):
    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"

    def __str__(self) -> str:
        return str(self.value)
