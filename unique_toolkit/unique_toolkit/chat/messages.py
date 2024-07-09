from enum import StrEnum
from typing import List

from pydantic import BaseModel, RootModel


class AIMessageRole(StrEnum):
    USER = "user"
    SYSTEM = "system"


class AIMessage(BaseModel):
    role: AIMessageRole
    content: str

class AIMessageList(RootModel):
    root: List[AIMessage]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]
