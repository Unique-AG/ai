from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from unique_search_proxy.web.core.crawlers.base import BaseCrawler
from unique_search_proxy.web.core.errors import EngineNotConfiguredError
from unique_search_proxy.web.core.search_engines.base import SearchEngine
from unique_search_proxy.web.core.search_engines.config_types import (
    ENGINE_NAME_TO_CONFIG,
)
from unique_search_proxy.web.core.search_engines.descriptor import (
    SearchEngineDescriptor,
)

SearchEngineT = TypeVar("SearchEngineT", bound=SearchEngine)
CrawlerT = TypeVar("CrawlerT", bound=BaseCrawler)

_SEARCH_ENGINE_REGISTRY: dict[str, type[SearchEngine]] = {}
_SEARCH_ENGINE_DESCRIPTORS: dict[str, SearchEngineDescriptor] = {}
_CRAWLER_REGISTRY: dict[str, type[BaseCrawler]] = {}

_SEARCH_ENGINE_CONFIG_MODELS: dict[str, type[BaseModel]] = {}
_CRAWLER_CONFIG_MODELS: dict[str, type[BaseModel]] = {}


def register_search_engine(
    engine_id: str,
    engine_cls: type[SearchEngineT],
    *,
    config_model: type[BaseModel] | None = None,
    descriptor: SearchEngineDescriptor | None = None,
) -> type[SearchEngineT]:
    _SEARCH_ENGINE_REGISTRY[engine_id] = engine_cls
    if descriptor is not None:
        _SEARCH_ENGINE_DESCRIPTORS[engine_id] = descriptor
        _SEARCH_ENGINE_CONFIG_MODELS[engine_id] = descriptor.config_model
    elif config_model is not None:
        _SEARCH_ENGINE_CONFIG_MODELS[engine_id] = config_model
        _SEARCH_ENGINE_DESCRIPTORS[engine_id] = SearchEngineDescriptor(
            config_model=config_model,
            service_cls=engine_cls,
        )
    return engine_cls


def get_search_engine_descriptor(engine_id: str) -> SearchEngineDescriptor | None:
    return _SEARCH_ENGINE_DESCRIPTORS.get(engine_id.lower())


def register_crawler(
    crawler_id: str,
    crawler_cls: type[CrawlerT],
    *,
    config_model: type[BaseModel] | None = None,
) -> type[CrawlerT]:
    _CRAWLER_REGISTRY[crawler_id] = crawler_cls
    if config_model is not None:
        _CRAWLER_CONFIG_MODELS[crawler_id] = config_model
    return crawler_cls


def registered_search_engines() -> frozenset[str]:
    return frozenset(_SEARCH_ENGINE_REGISTRY)


def registered_crawlers() -> frozenset[str]:
    return frozenset(_CRAWLER_REGISTRY)


def get_search_engine(engine_id: str) -> type[SearchEngine]:
    engine_cls = _SEARCH_ENGINE_REGISTRY.get(engine_id)
    if engine_cls is None:
        raise EngineNotConfiguredError(engine_id, kind="engine")
    return engine_cls


def get_crawler(crawler_id: str) -> type[BaseCrawler]:
    crawler_cls = _CRAWLER_REGISTRY.get(crawler_id)
    if crawler_cls is None:
        raise EngineNotConfiguredError(crawler_id, kind="crawler")
    return crawler_cls


def build_search_engine_config_union() -> list[type[BaseModel]]:
    """Registered per-engine config models for discriminated-union assembly."""
    registered = list(_SEARCH_ENGINE_CONFIG_MODELS.values())
    if registered:
        return registered
    return list(ENGINE_NAME_TO_CONFIG.values())


def build_crawler_config_union() -> list[type[BaseModel]]:
    return list(_CRAWLER_CONFIG_MODELS.values())


def get_search_engine_config_model(engine_id: str) -> type[BaseModel] | None:
    return _SEARCH_ENGINE_CONFIG_MODELS.get(engine_id.lower())


def get_crawler_config_model(crawler_id: str) -> type[BaseModel] | None:
    return _CRAWLER_CONFIG_MODELS.get(crawler_id.lower())


def clear_registries_for_tests() -> None:
    _SEARCH_ENGINE_REGISTRY.clear()
    _SEARCH_ENGINE_DESCRIPTORS.clear()
    _CRAWLER_REGISTRY.clear()
    _SEARCH_ENGINE_CONFIG_MODELS.clear()
    _CRAWLER_CONFIG_MODELS.clear()
