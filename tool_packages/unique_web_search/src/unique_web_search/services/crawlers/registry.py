"""Crawler self-registration registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.crawlers.base import CrawlerType

from unique_web_search.services._registry import BaseSpec, Registry
from unique_web_search.services.search_engine.registry import with_config_display_title


@dataclass(frozen=True)
class CrawlerSpec(BaseSpec[CrawlerType]):
    config_display_name: str


CRAWLER_REGISTRY: Registry[CrawlerType, CrawlerSpec] = Registry(CrawlerSpec)


def register_crawler(
    *,
    name: str,
    key: CrawlerType,
    config_cls: type[BaseModel],
    config_display_name: str,
) -> Callable[[type], type]:
    """Register a crawler and apply ``config_display_name`` to its config schema title."""
    titled_config_cls = with_config_display_title(config_cls, config_display_name)
    return CRAWLER_REGISTRY.register(
        name=name,
        key=key,
        config_cls=titled_config_cls,
        config_display_name=config_display_name,
    )


def get_crawler_service(
    crawler_config: object,
    *,
    request_context: RequestContext = LOCAL_REQUEST_CONTEXT,
):
    crawler = getattr(crawler_config, "crawler")
    return CRAWLER_REGISTRY[crawler].impl_cls(
        crawler_config,
        request_context=request_context,
    )


__all__ = [
    "CRAWLER_REGISTRY",
    "CrawlerSpec",
    "get_crawler_service",
    "register_crawler",
]
