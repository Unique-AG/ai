import json

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    data: str | dict

    @field_validator("chat_id", "message_id", mode="before")
    def validate_chat_id_or_message_id(cls, v, info):
        field_name = info.field_name
        data = info.data

        # Get the other field's value
        other_field = "message_id" if field_name == "chat_id" else "chat_id"
        other_value = data.get(other_field)

        # Check if both are None
        if v is None and other_value is None:
            camel_name = camelize(field_name)
            raise ValueError(
                f"Either {camel_name} or messageId must be provided"
                if field_name == "chat_id"
                else f"Either chatId or {camel_name} must be provided"
            )

        return v

    @field_validator("data", mode="before")
    def validate_data(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
