from __future__ import annotations

from enum import StrEnum
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.param_policy.derive import derive_request_model
from unique_search_proxy_core.param_policy.exposable_config import (
    ExposableParamsConfig,
)
from unique_search_proxy_core.param_policy.request_base import SearchRequestBase
from unique_search_proxy_core.search_engines.base import SearchEngineType


class CustomApiRequestMethod(StrEnum):
    GET = "GET"
    POST = "POST"


class CustomApiConfig(ExposableParamsConfig):
    """Tenant-configured search endpoint executed by Search Proxy."""

    _request_model_name: ClassVar[str] = "CustomApiSearchRequest"
    _exposed_params_model_name: ClassVar[str] = "CustomApiExposedParams"

    engine: Annotated[
        Literal[SearchEngineType.CUSTOM_API], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=SearchEngineType.CUSTOM_API,
        title="Search engine",
        description="Provider discriminator; must be `custom_api` for this config.",
    )
    api_endpoint: str = Field(
        default="https://api.example.com/search",
        title="API endpoint",
        description="HTTP(S) endpoint called by Search Proxy.",
    )
    api_headers: str = Field(
        default='{"Content-Type": "application/json"}',
        title="API headers",
        description="JSON object containing headers sent to the custom API.",
    )
    api_additional_query_params: str = Field(
        default="{}",
        title="Additional query parameters",
        description="JSON object merged into the custom API query parameters.",
    )
    api_additional_body_params: str = Field(
        default="{}",
        title="Additional body parameters",
        description="JSON object merged into the custom API JSON body.",
    )
    api_request_method: CustomApiRequestMethod = Field(
        default=CustomApiRequestMethod.GET,
        title="Request method",
        description="HTTP method used to call the custom API.",
    )
    timeout: int = Field(
        default=120,
        description="Custom API request timeout in seconds.",
    )

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        return derive_request_model(
            cls,
            base=SearchRequestBase,
            name=cls._request_model_name,
        )


CustomApiSearchRequest = CustomApiConfig.request_model()


__all__ = [
    "CustomApiConfig",
    "CustomApiRequestMethod",
    "CustomApiSearchRequest",
]
