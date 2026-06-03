"""Convert application Pydantic config models to OpenAPI-generated SDK models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from unique_search_proxy.sdk._generated.models.basic_crawler_config import (
    BasicCrawlerConfig as SdkBasicCrawlerConfig,
)
from unique_search_proxy.sdk._generated.models.google_config import (
    GoogleConfig as SdkGoogleConfig,
)
from unique_search_proxy.sdk._generated.models.google_config_request import (
    GoogleConfigRequest as SdkGoogleConfigRequest,
)
from unique_search_proxy.web.core.crawlers.config_types import CrawlerConfigTypes
from unique_search_proxy.web.core.param_policy.exposable_param import ExposableParam
from unique_search_proxy.web.core.search_engines.config_types import (
    SearchEngineConfigTypes,
)
from unique_search_proxy.web.core.search_engines.google.schema import (
    GoogleSearchRequest,
)


def _model_to_sdk_dict(model: BaseModel) -> dict[str, Any]:
    data = model.model_dump(mode="json", by_alias=True, exclude_none=True)
    for name, field in type(model).model_fields.items():
        raw = getattr(model, name)
        if isinstance(raw, ExposableParam):
            key = field.serialization_alias or field.alias or name
            data[key] = raw.model_dump(mode="json", by_alias=True)
    return data


def to_sdk_crawler_config(config: CrawlerConfigTypes) -> SdkBasicCrawlerConfig:
    return SdkBasicCrawlerConfig.from_dict(_model_to_sdk_dict(config))


def to_sdk_google_config(config: SearchEngineConfigTypes) -> SdkGoogleConfig:
    return SdkGoogleConfig.from_dict(_model_to_sdk_dict(config))


def to_sdk_google_config_request(
    request: GoogleSearchRequest,
) -> SdkGoogleConfigRequest:
    return SdkGoogleConfigRequest.from_dict(_model_to_sdk_dict(request))
