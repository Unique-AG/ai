from pydantic import BaseModel, ConfigDict


class StructuredOutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
