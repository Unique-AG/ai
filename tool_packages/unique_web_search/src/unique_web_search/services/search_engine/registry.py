"""Search-engine self-registration registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from pydantic import BaseModel, ConfigDict, create_model
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


def with_config_display_title(
    config_cls: type[BaseModel],
    display_name: str,
) -> type[BaseModel]:
    """Return a config model subclass whose JSON schema title is ``display_name``."""
    if config_cls.model_config.get("title") == display_name:
        return config_cls
    return create_model(
        config_cls.__name__,
        __base__=config_cls,
        __config__=get_configuration_dict(title=display_name),
    )


def register_search_engine(
    *,
    name: str,
    key: EngineKey,
    config_cls: type[BaseModel],
    mode: SearchEngineMode,
    config_display_name: str,
    needs_language_model: bool = False,
) -> Callable[[type], type]:
    """Register a search engine and apply ``config_display_name`` to its config schema title."""
    titled_config_cls = with_config_display_title(config_cls, config_display_name)
    return SEARCH_ENGINE_REGISTRY.register(
        name=name,
        key=key,
        config_cls=titled_config_cls,
        mode=mode,
        config_display_name=config_display_name,
        needs_language_model=needs_language_model,
    )


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


def resolve_search_engine_mode(search_engine_config: object) -> SearchEngineMode:
    """Resolve a config's mode, honoring a CustomAPI ``search_engine_mode`` override.

    Only ``CustomAPIConfig`` carries a ``search_engine_mode`` field; for every other
    engine the attribute is absent and the registry default applies.
    """
    override = getattr(search_engine_config, "search_engine_mode", None)
    return get_search_engine_mode(
        getattr(search_engine_config, "engine"),
        override=override,
    )


def get_search_engine_model_config(
    search_engine_name: EngineKey,
) -> ConfigDict:
    config_cls = SEARCH_ENGINE_REGISTRY[search_engine_name].config_cls
    return cast(ConfigDict, config_cls.model_config)
