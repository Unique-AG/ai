from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseAPIModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        use_enum_values=True,
    )
