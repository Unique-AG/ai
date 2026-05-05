from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model

from unique_mcp.meta_keys import CONFIG_SCHEMA_META_KEY

CONTEXT_REQUIREMENTS_META_KEY = "unique.app/context-requirements"


class ContextRequirements(BaseModel):
    """Declares which ``_meta`` keys a tool expects on every ``callTool``."""

    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    accepts_custom: bool = False

    def to_tool_meta(self) -> dict[str, object]:
        return {CONTEXT_REQUIREMENTS_META_KEY: self.model_dump(mode="json")}


def config_schema_meta(config_model: type[BaseModel]) -> dict[str, Any]:
    """Generate the config-schema meta entry for a tool.

    The returned dict is meant to be merged into the tool's ``meta`` dict at
    registration time (via :func:`merge_tool_meta`).  The host reads this entry
    from ``listTools`` to store the schema and render the RJSF config form in
    the admin UI.

    Args:
        config_model: A Pydantic ``BaseModel`` subclass annotated with
            ``RJSFMetaTag`` entries.  Must be instantiatable with no arguments
            (all fields have defaults) so that ``default_config`` can be derived.

    Returns:
        ``{ CONFIG_SCHEMA_META_KEY: { json_schema, ui_schema, default_config } }``
    """
    return {
        CONFIG_SCHEMA_META_KEY: {
            "json_schema": config_model.model_json_schema(),
            "ui_schema": ui_schema_for_model(config_model),
            "default_config": config_model().model_dump(mode="json", by_alias=True),
        }
    }


def merge_tool_meta(
    base: dict[str, object] | None,
    requirements: ContextRequirements,
    *,
    config_model: type[BaseModel] | None = None,
) -> dict[str, object]:
    """Merge base meta, context requirements, and an optional config schema.

    Args:
        base: Existing meta dict (e.g. ``{"unique.app/icon": "search"}``).
        requirements: Declares which ``_meta`` keys the tool expects at call
            time (auth + chat namespaces only).
        config_model: Optional Pydantic model whose RJSF schema should be
            embedded in the tool meta under ``CONFIG_SCHEMA_META_KEY``.
            When present the host stores the schema and injects the resolved
            config under ``CONFIG_META_KEY`` at call time.

    Returns:
        Merged meta dict ready to pass as the ``meta`` argument to
        ``@mcp.tool()``.
    """
    out: dict[str, object] = dict(base or {})
    out.update(requirements.to_tool_meta())
    if config_model is not None:
        out.update(config_schema_meta(config_model))
    return out


__all__ = [
    "CONTEXT_REQUIREMENTS_META_KEY",
    "ContextRequirements",
    "config_schema_meta",
    "merge_tool_meta",
]
