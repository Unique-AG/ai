"""Convert core Pydantic request models to OpenAPI-generated SDK models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.search_engines.base import SearchEngineType

from unique_search_proxy_sdk._generated.models.basic_crawler_request import (
    BasicCrawlerRequest as SdkBasicCrawlerRequest,
)
from unique_search_proxy_sdk._generated.models.google_request import (
    GoogleRequest as SdkGoogleRequest,
)


def _model_to_sdk_dict(model: BaseModel) -> dict[str, Any]:
    data = model.model_dump(mode="json", by_alias=True, exclude_none=True)
    for name, field in type(model).model_fields.items():
        raw = getattr(model, name)
        if isinstance(raw, ExposableParam):
            key = field.serialization_alias or field.alias or name
            data[key] = raw.model_dump(mode="json", by_alias=True)
    return data


def to_sdk_google_request(request: BaseModel) -> SdkGoogleRequest:
    return SdkGoogleRequest.from_dict(_model_to_sdk_dict(request))


def to_sdk_crawl_request(request: BaseModel) -> SdkBasicCrawlerRequest:
    return SdkBasicCrawlerRequest.from_dict(_model_to_sdk_dict(request))


def to_sdk_search_request(request: BaseModel) -> SdkGoogleRequest:
    """Dispatch flat search request to the generated SDK model for its engine."""
    engine = getattr(request, "engine", None)
    if engine is None:
        raise ValueError("Search request is missing engine discriminator")
    engine_id = engine.value if hasattr(engine, "value") else str(engine)
    if engine_id == SearchEngineType.GOOGLE.value:
        return to_sdk_google_request(request)
    raise ValueError(f"No SDK converter for search engine {engine_id!r}")
