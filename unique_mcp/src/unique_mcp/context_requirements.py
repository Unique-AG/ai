"""Tool-level declaration of the ``_meta`` keys an MCP tool needs at call time.

MCP servers publish this declaration as part of a tool's static ``meta`` (the
dict returned by ``listTools``) under the
:data:`CONTEXT_REQUIREMENTS_META_KEY` namespace. The host (monorepo) reads
the cached declaration once per tool and intersects it with the per-server
admin allow-list to decide which keys to forward in each ``callTool``
request's ``_meta``.

The declaration lives on the **tool definition** (Layer 1). It is never a
request ``_meta`` key (Layer 3).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

CONTEXT_REQUIREMENTS_META_KEY = "unique.app/context-requirements"


class ContextRequirements(BaseModel):
    """Declares which ``_meta`` keys a tool expects on every ``callTool``.

    Keys should be fully-qualified ``unique.app/...`` names (see
    :class:`unique_mcp.meta_keys.MetaKeys`). Server-specific custom keys are
    allowed when :attr:`accepts_custom` is ``True``; whether a host forwards
    them is still subject to the admin allow-list.
    """

    required: list[str] = Field(
        default_factory=list,
        description=(
            "Keys that MUST be present in the request `_meta` for the tool to "
            "function correctly."
        ),
    )
    optional: list[str] = Field(
        default_factory=list,
        description=("Keys the tool will consume when present but does not require."),
    )
    accepts_custom: bool = Field(
        default=False,
        description=(
            "If true, the tool is prepared to consume admin-configured custom "
            "keys in addition to `required`/`optional`."
        ),
    )

    def to_tool_meta(self) -> dict[str, object]:
        """Return the declaration as a ``{CONTEXT_REQUIREMENTS_META_KEY: ...}`` dict.

        Suitable for passing (merged) into the ``meta`` argument of
        ``FastMCP.tool(...)``.
        """
        return {CONTEXT_REQUIREMENTS_META_KEY: self.model_dump(mode="json")}


def merge_tool_meta(
    base: dict[str, object] | None,
    requirements: ContextRequirements,
) -> dict[str, object]:
    """Merge a :class:`ContextRequirements` declaration into existing tool meta.

    Existing keys in ``base`` are preserved; the
    :data:`CONTEXT_REQUIREMENTS_META_KEY` entry is overwritten so callers can
    rely on the returned dict reflecting the supplied ``requirements``.
    """
    out: dict[str, object] = dict(base or {})
    out.update(requirements.to_tool_meta())
    return out


__all__ = [
    "CONTEXT_REQUIREMENTS_META_KEY",
    "ContextRequirements",
    "merge_tool_meta",
]
