"""Values that import nothing else in this package."""

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """Frozen strict model. Other models inherit this."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
