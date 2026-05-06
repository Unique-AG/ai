from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable


@runtime_checkable
class MetaPart(Protocol):
    _META_KEY: ClassVar[str]

    def merge_into_meta(self, meta: dict[str, Any]) -> None: ...


__all__ = ["MetaPart"]
