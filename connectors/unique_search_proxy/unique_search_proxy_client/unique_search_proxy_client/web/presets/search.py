"""Search payload presets for Swagger and dev CLI."""

from __future__ import annotations

from unique_search_proxy_client.web.presets.types import PresetDefinition

SEARCH_PRESETS: tuple[PresetDefinition, ...] = (
    PresetDefinition(
        id="google_minimal",
        summary="Google search (minimal)",
        description=(
            "Flat search request; requires GOOGLE_SEARCH_API_KEY and "
            "GOOGLE_SEARCH_ENGINE_ID in .env."
        ),
        kind="search",
        provider_id="google",
    ),
    PresetDefinition(
        id="google_with_gl",
        summary="Google search (with gl and dateRestrict)",
        description=(
            "Google search with geolocation and recency filters. Requires "
            "GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env."
        ),
        kind="search",
        provider_id="google",
        overrides={
            "gl": "ch",
            "dateRestrict": "d7",
        },
    ),
    PresetDefinition(
        id="brave_minimal",
        summary="Brave search (minimal)",
        description="Flat search request; requires BRAVE_SEARCH_API_KEY in .env.",
        kind="search",
        provider_id="brave",
    ),
    PresetDefinition(
        id="perplexity_minimal",
        summary="Perplexity search (minimal)",
        description=(
            "Flat search request; requires PERPLEXITY_SEARCH_API_KEY in .env."
        ),
        kind="search",
        provider_id="perplexity",
    ),
)

__all__ = ["SEARCH_PRESETS"]
