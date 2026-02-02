import json
from typing import Any, Literal, TypeVar

from httpx import AsyncClient
from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)
from unique_web_search.settings import CUSTOM_API_REQUEST_METHOD, env_settings

T = TypeVar("T")


def conditional_type(tp: type[T], value: T | None, description: str, default: T):
    if value is None:
        return tp, Field(default=default, description=description)
    else:
        return SkipJsonSchema[tp], Field(default=value, description=description)


ApiEndpointType, ApiEndpointField = conditional_type(
    str,
    env_settings.custom_web_search_api_endpoint,
    "The URL of the custom API",
    "http://api.example.com",
)
ApiHeadersType, ApiHeadersField = conditional_type(
    str,
    env_settings.custom_web_search_api_headers,
    "The headers of the custom API",
    '{"Content-Type": "application/json"}',
)
ApiAdditionalQueryParamsType, ApiAdditionalQueryParamsField = conditional_type(
    str,
    env_settings.custom_web_search_api_additional_query_params,
    "The additional parameters of the custom API",
    "{}",
)
ApiAdditionalBodyParamsType, ApiAdditionalBodyParamsField = conditional_type(
    str,
    env_settings.custom_web_search_api_additional_body_params,
    "The additional body of the custom API",
    "{}",
)
ApiRequestMethodType, ApiRequestMethodField = conditional_type(
    CUSTOM_API_REQUEST_METHOD,
    env_settings.custom_web_search_api_method,
    "The request method of the custom API",
    CUSTOM_API_REQUEST_METHOD.GET,
)


class CustomAPIConfig(BaseSearchEngineConfig[SearchEngineType.CUSTOM_API]):
    search_engine_name: Literal[SearchEngineType.CUSTOM_API] = (
        SearchEngineType.CUSTOM_API
    )
    api_endpoint: ApiEndpointType = ApiEndpointField  # type: ignore (Dynamic type generation)
    api_headers: ApiHeadersType = ApiHeadersField  # type: ignore (Dynamic type generation)
    api_additional_query_params: ApiAdditionalQueryParamsType = (  # type: ignore (Dynamic type generation)
        ApiAdditionalQueryParamsField
    )
    api_additional_body_params: ApiAdditionalBodyParamsType = (  # type: ignore (Dynamic type generation)
        ApiAdditionalBodyParamsField
    )
    api_request_method: ApiRequestMethodType = ApiRequestMethodField  # type: ignore (Dynamic type generation)
    requires_scraping: bool = Field(
        default=False, description="Whether the search engine requires scraping"
    )
    timeout: int = Field(default=120, description="The timeout of the custom API")


class CustomAPI(SearchEngine[CustomAPIConfig]):
    def __init__(self, config: CustomAPIConfig):
        super().__init__(config)
        self.api_endpoint = config.api_endpoint
        self.is_configured = True  # No possibility to check if the API is configured from our side. So we assume it is configured.

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        params, body = self._prepare_request_params_and_body(query)

        async_client_params = self._client_config | {
            "timeout": self.config.timeout,
        }
        async with AsyncClient(**async_client_params) as client:
            response = await client.request(
                method=self._request_method,
                headers=self._headers,
                url=self.api_endpoint,
                params=params,
                json=body,
            )

        if not response.is_success:
            raise ValueError(
                f"Search engine request failed with status {response.status_code}: {response.text}"
            )

        validated_response = WebSearchResults.model_validate(response.json())
        return validated_response.results

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    @property
    def _request_method(self) -> CUSTOM_API_REQUEST_METHOD:
        return self.config.api_request_method

    @property
    def _headers(self) -> dict[str, str]:
        return json.loads(self.config.api_headers)

    @property
    def _additional_query_params(self) -> dict[str, str]:
        return json.loads(self.config.api_additional_query_params)

    @property
    def _additional_body_params(self) -> dict[str, str]:
        return json.loads(self.config.api_additional_body_params)

    @property
    def _client_config(self) -> dict[str, Any]:
        if env_settings.custom_web_search_api_client_config is None:
            return {}
        return json.loads(env_settings.custom_web_search_api_client_config)

    def _prepare_request_params_and_body(self, query: str) -> tuple[dict, dict]:
        params = self._additional_query_params
        body = self._additional_body_params

        if self._request_method == CUSTOM_API_REQUEST_METHOD.GET:
            params = params | {"query": query}
        else:
            body = body | {"query": query}

        return params, body
