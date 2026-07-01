"""Search-engine self-registration registry."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ConfigDict
from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model import LanguageModelService

from unique_web_search.services._registry import BaseSpec, Registry
from unique_web_search.services.search_engine.base import (
    LocalSearchEngineType,
    SearchEngineMode,
)

EngineKey = SearchEngineType | AgentEngineType | LocalSearchEngineType


@dataclass(frozen=True)
class SearchEngineSpec(BaseSpec[EngineKey]):
    mode: SearchEngineMode
    config_display_name: str
    needs_language_model: bool = False


SEARCH_ENGINE_REGISTRY: Registry[EngineKey, SearchEngineSpec] = Registry(
    SearchEngineSpec
)
register_search_engine = SEARCH_ENGINE_REGISTRY.register


def get_search_engine_service(
    search_engine_config: object,
    language_model_service: LanguageModelService,
):
    engine = getattr(search_engine_config, "engine")
    spec = SEARCH_ENGINE_REGISTRY[engine]
    if spec.needs_language_model:
        return spec.impl_cls(search_engine_config, language_model_service)
    return spec.impl_cls(search_engine_config)


def get_search_engine_mode(
    engine_type: EngineKey,
    *,
    override: SearchEngineMode | None = None,
) -> SearchEngineMode:
    """Return the mode (standard vs agent) for a given search engine type."""
    if override is not None:
        return override
    return SEARCH_ENGINE_REGISTRY[engine_type].mode


def get_search_engine_model_config(
    search_engine_name: EngineKey,
) -> ConfigDict:
    return get_configuration_dict(
        title=SEARCH_ENGINE_REGISTRY[search_engine_name].config_display_name
    )
