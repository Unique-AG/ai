from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from unique_mcp.meta.keys import CONTEXT_REQUIREMENTS_META_KEY


class ContextRequirements(BaseModel):
    _META_KEY: ClassVar[str] = CONTEXT_REQUIREMENTS_META_KEY

    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    accepts_custom: bool = False

    def merge_into_meta(self, meta: dict[str, Any]) -> None:
        meta[self._META_KEY] = self.model_dump(mode="json")


__all__ = ["ContextRequirements"]
