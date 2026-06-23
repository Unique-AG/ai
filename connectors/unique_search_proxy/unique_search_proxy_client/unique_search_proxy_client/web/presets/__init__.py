"""Curated request payloads for Swagger examples and dev testing."""

from __future__ import annotations

from unique_search_proxy_client.web.presets.common import (
    DEFAULT_SEARCH_QUERY,
    EXAMPLE_URLS,
    EXAMPLE_URLS_MULTI,
    build_crawl_preset,
    build_search_preset,
)
from unique_search_proxy_client.web.presets.crawl import CRAWL_PRESETS
from unique_search_proxy_client.web.presets.search import SEARCH_PRESETS
from unique_search_proxy_client.web.presets.types import PresetDefinition, PresetKind

ALL_PRESETS: tuple[PresetDefinition, ...] = SEARCH_PRESETS + CRAWL_PRESETS

_PRESET_BY_ID: dict[str, PresetDefinition] = {
    preset.id: preset for preset in ALL_PRESETS
}


def get_preset(preset_id: str) -> PresetDefinition:
    preset = _PRESET_BY_ID.get(preset_id)
    if preset is None:
        known = ", ".join(sorted(_PRESET_BY_ID))
        raise KeyError(f"Unknown preset {preset_id!r}. Known presets: {known}")
    return preset


def list_presets(*, kind: PresetKind | None = None) -> list[PresetDefinition]:
    if kind is None:
        return list(ALL_PRESETS)
    return [preset for preset in ALL_PRESETS if preset.kind == kind]


__all__ = [
    "ALL_PRESETS",
    "CRAWL_PRESETS",
    "DEFAULT_SEARCH_QUERY",
    "EXAMPLE_URLS",
    "EXAMPLE_URLS_MULTI",
    "PresetDefinition",
    "PresetKind",
    "SEARCH_PRESETS",
    "build_crawl_preset",
    "build_search_preset",
    "get_preset",
    "list_presets",
]
