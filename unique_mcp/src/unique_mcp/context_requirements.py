from __future__ import annotations

from pydantic import BaseModel, Field

CONTEXT_REQUIREMENTS_META_KEY = "unique.app/context-requirements"


class ContextRequirements(BaseModel):
    """Declares which ``_meta`` keys a tool expects on every ``callTool``."""

    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    accepts_custom: bool = False

    def to_tool_meta(self) -> dict[str, object]:
        return {CONTEXT_REQUIREMENTS_META_KEY: self.model_dump(mode="json")}


def merge_tool_meta(
    base: dict[str, object] | None,
    requirements: ContextRequirements,
) -> dict[str, object]:
    out: dict[str, object] = dict(base or {})
    out.update(requirements.to_tool_meta())
    return out


__all__ = [
    "CONTEXT_REQUIREMENTS_META_KEY",
    "ContextRequirements",
    "merge_tool_meta",
]
