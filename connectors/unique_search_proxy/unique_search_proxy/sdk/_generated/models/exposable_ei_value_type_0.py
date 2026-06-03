from enum import Enum


class ExposableEIValueType0(str, Enum):
    E = "e"
    I = "i"

    def __str__(self) -> str:
        return str(self.value)
