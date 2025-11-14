import json
from typing import Self

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


class ShortTermMemory(BaseModel):
    model_config = model_config

    id: str
    key: str = Field(alias="object")
    chat_id: str | None
    message_id: str | None
    data: str | dict | int | float | bool | list | None

    @model_validator(mode="after")
    def validate_chat_id_or_message_id(self) -> Self:
        if self.chat_id is None and self.message_id is None:
            raise ValueError("Either chat_id or message_id must be provided")
        return self

    @field_validator("data", mode="before")
    def validate_data(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
