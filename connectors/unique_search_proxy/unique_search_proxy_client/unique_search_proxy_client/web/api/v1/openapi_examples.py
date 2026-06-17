"""Swagger UI example adapter — maps preset catalog to FastAPI Example objects."""

from __future__ import annotations

from fastapi.openapi.models import Example

from unique_search_proxy_client.web.presets import CRAWL_PRESETS, SEARCH_PRESETS
from unique_search_proxy_client.web.presets.types import PresetDefinition


def _to_openapi_example(preset: PresetDefinition) -> Example:
    return Example(
        summary=preset.summary,
        description=preset.description,
        value=preset.build_payload(),
    )


SEARCH_OPENAPI_EXAMPLES: dict[str, Example] = {
    preset.id: _to_openapi_example(preset) for preset in SEARCH_PRESETS
}

CRAWL_OPENAPI_EXAMPLES: dict[str, Example] = {
    preset.id: _to_openapi_example(preset) for preset in CRAWL_PRESETS
}
