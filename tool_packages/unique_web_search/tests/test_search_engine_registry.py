"""Tests for the search-engine self-registration registry."""

from __future__ import annotations

import pytest
from unique_search_proxy_core.agent_engines import AgentEngineType
from unique_search_proxy_core.search_engines import SearchEngineType

from unique_web_search.services.search_engine import (
    BingSearchConfig,
    BraveConfig,
    CustomAPIConfig,
    GoogleConfig,
    PerplexityConfig,
    VertexAIConfig,
)
from unique_web_search.services.search_engine.base import LocalSearchEngineType
from unique_web_search.services.search_engine.registry import SEARCH_ENGINE_REGISTRY

_EXPECTED_CONFIG_BASES: dict[
    SearchEngineType | AgentEngineType | LocalSearchEngineType,
    type,
] = {
    SearchEngineType.GOOGLE: GoogleConfig,
    SearchEngineType.BRAVE: BraveConfig,
    SearchEngineType.PERPLEXITY: PerplexityConfig,
    AgentEngineType.BING: BingSearchConfig,
    AgentEngineType.VERTEXAI: VertexAIConfig,
    LocalSearchEngineType.CUSTOM_API: CustomAPIConfig,
}


def test_search_engine_registry__autodiscover__registers_all_engines() -> None:
    assert len(SEARCH_ENGINE_REGISTRY.specs) == 6


def test_search_engine_registry__enum_coverage__includes_all_discriminators() -> None:
    SEARCH_ENGINE_REGISTRY.assert_enum_coverage(
        SearchEngineType,
        AgentEngineType,
        LocalSearchEngineType,
    )


def test_search_engine_registry__config_classes__extend_static_bases() -> None:
    for spec in SEARCH_ENGINE_REGISTRY.specs:
        base_cls = _EXPECTED_CONFIG_BASES[spec.key]
        assert issubclass(spec.config_cls, base_cls)
        assert (
            spec.config_cls.model_json_schema().get("title") == spec.config_display_name
        )


@pytest.mark.parametrize(
    ("engine_key", "needs_language_model"),
    [
        (SearchEngineType.GOOGLE, False),
        (SearchEngineType.BRAVE, False),
        (SearchEngineType.PERPLEXITY, False),
        (AgentEngineType.BING, True),
        (AgentEngineType.VERTEXAI, True),
        (LocalSearchEngineType.CUSTOM_API, False),
    ],
    ids=["google", "brave", "perplexity", "bing", "vertexai", "custom_api"],
)
def test_search_engine_registry__needs_language_model__per_engine(
    engine_key: SearchEngineType | AgentEngineType | LocalSearchEngineType,
    needs_language_model: bool,
) -> None:
    assert (
        SEARCH_ENGINE_REGISTRY[engine_key].needs_language_model is needs_language_model
    )


def test_search_engine_registry__name_to_config__has_expected_keys() -> None:
    assert set(SEARCH_ENGINE_REGISTRY.name_to_config()) == {
        "google",
        "bing",
        "brave",
        "perplexity",
        "vertexai",
        "custom_api",
    }
