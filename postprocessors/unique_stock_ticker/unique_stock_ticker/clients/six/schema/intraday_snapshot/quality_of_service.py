from enum import StrEnum


class QualityOfService(StrEnum):
    DELAYED = "DELAYED"
    REAL_TIME = "REAL_TIME"
    END_OF_DAY = "END_OF_DAY"
    PREVIOUS_DAY = "PREVIOUS_DAY"
