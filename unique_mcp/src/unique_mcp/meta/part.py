from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable


@runtime_checkable
class MetaPart(Protocol):
    _META_KEY: ClassVar[str]

    def merge_into_meta(self, meta: dict[str, Any]) -> None: ...


def merge_tool_meta(
    base: dict[str, Any] | None,
    *parts: MetaPart,
) -> dict[str, Any]:
    """Merge base meta with zero or more MetaPart contributions.

    Args:
        base: Existing meta dict (e.g. ``{"unique.app/icon": "search"}``).
        *parts: Any number of :class:`MetaPart` instances; each contributes
            one key to the merged dict.

    Returns:
        New dict — ``base`` is never mutated.
    """
    out: dict[str, Any] = dict(base or {})
    for part in parts:
        part.merge_into_meta(out)
    return out


__all__ = ["MetaPart", "merge_tool_meta"]
