import json
from typing import Any

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
    data: str | dict | int | float | bool | list | None = Field(deprecated=True)
    value: str | dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _data_to_value(self) -> "ShortTermMemory":
        if isinstance(self.data, dict):
            self.value = self.data
        elif isinstance(self.data, str):
            try:
                self.value = json.loads(self.data)
            except json.JSONDecodeError:
                self.value = self.data
        elif self.data is None:
            self.value = ""
        else:
            self.value = str(self.data)
        return self

    @model_validator(mode="after")
    def validate_message_id_and_chat_id(self):
        if (self.message_id is None and self.chat_id is None) or (
            self.message_id is not None and self.chat_id is not None
        ):
            raise ValueError("Either message_id or chat_id must be provided")
        return self

    @field_validator("data", mode="before")
    def validate_data(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
