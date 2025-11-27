from typing import Literal, TypeVar

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
from unique_web_search.settings import env_settings

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
    dict[str, str],
    env_settings.custom_web_search_api_headers,
    "The headers of the custom API",
    {"Content-Type": "application/json"},
)
ApiAdditionalParamsType, ApiAdditionalParamsField = conditional_type(
    dict[str, int | str | bool],
    env_settings.custom_web_search_api_additional_params,
    "The additional parameters of the custom API",
    {},
)


class CustomAPIConfig(BaseSearchEngineConfig[SearchEngineType.CUSTOM_API]):
    search_engine_name: Literal[SearchEngineType.CUSTOM_API] = (
        SearchEngineType.CUSTOM_API
    )
    api_endpoint: ApiEndpointType = ApiEndpointField  # type: ignore (Dynamic type generation)
    api_headers: ApiHeadersType = ApiHeadersField  # type: ignore (Dynamic type generation)
    api_additional_params: ApiAdditionalParamsType = ApiAdditionalParamsField  # type: ignore (Dynamic type generation)
    requires_scraping: bool = Field(
        default=False, description="Whether the search engine requires scraping"
    )
    timeout: int = Field(default=120, description="The timeout of the custom API")


class CustomAPI(SearchEngine[CustomAPIConfig]):
    def __init__(self, config: CustomAPIConfig):
        super().__init__(config)
        self.api_endpoint = config.api_endpoint

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        params = {
            "query": query,
            **self.config.api_additional_params,
        }
        headers = {
            **self.config.api_headers,
        }
        async with AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self.api_endpoint, json=params, headers=headers
            )

        validated_response = WebSearchResults.model_validate(response.json())
        return validated_response.results

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping
