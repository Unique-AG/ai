"""Preset catalog types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from unique_search_proxy_client.web.presets.common import (
    build_crawl_preset,
    build_search_preset,
)

PresetKind = Literal["search", "crawl"]


@dataclass(frozen=True)
class PresetDefinition:
    """Declarative preset entry; payload is built on demand."""

    id: str
    summary: str
    description: str
    kind: PresetKind
    provider_id: str
    overrides: dict[str, Any] = field(default_factory=dict)

    def build_payload(self) -> dict[str, Any]:
        if self.kind == "search":
            return build_search_preset(self.provider_id, self.overrides)
        return build_crawl_preset(self.provider_id, self.overrides)


__all__ = ["PresetDefinition", "PresetKind"]
