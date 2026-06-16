from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field

from unique_search_proxy_core.model_derivation import derive_request_model

URLS_FIELD = "urls"


def _crawl_request_model_name(config_cls: type[BaseModel]) -> str:
    """``BasicConfig`` -> ``BasicCrawlRequest``."""
    base = config_cls.__name__
    if base.endswith("Config"):
        base = base[: -len("Config")]
    return f"{base}CrawlRequest"


@lru_cache(maxsize=32)
def build_crawl_request_model(config_cls: type[BaseModel]) -> type[BaseModel]:
    """Derive ``POST /v1/crawl`` body: ``urls`` + all config fields."""
    return derive_request_model(
        config_cls,
        leading_fields=(
            (
                URLS_FIELD,
                (
                    list[str],
                    Field(
                        ...,
                        min_length=1,
                        description="URLs to crawl",
                    ),
                ),
            ),
        ),
        model_name=_crawl_request_model_name,
        unwrap_exposable_params=False,
    )


__all__ = ["URLS_FIELD", "build_crawl_request_model"]
