import json
import logging
from typing import Any, TypeVar, override

from httpx import AsyncClient
from pydantic import BaseModel, Field, model_validator
from pydantic.json_schema import SkipJsonSchema
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.custom_api.schema import (
    CustomApiConfig as ProxyCustomApiConfig,
)
from unique_search_proxy_core.search_engines.custom_api.schema import (
    CustomApiSearchRequest,
)
from unique_search_proxy_core.url_safety import (
    CrawlTargetValidationError,
    UrlSafetyService,
)
from unique_toolkit.agentic.feature_flags import FeatureFlagNames
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.experimental.resources.feature_flags import is_flag_enabled

from unique_web_search.metrics import custom_api_url_safety_report
from unique_web_search.services.search_engine.base import (
    LocalSearchEngineType,
    SearchEngine,
    SearchEngineMode,
)
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)
from unique_web_search.settings import CUSTOM_API_REQUEST_METHOD, env_settings

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def conditional_type(tp: type[T], value: T | None, description: str, default: T):
    if value is None:
        return tp, Field(default=default, description=description)
    else:
        return SkipJsonSchema[tp], Field(
            default=value, description=description, exclude=True
        )


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


class CustomAPIConfig(ProxyCustomApiConfig):
    model_config = get_configuration_dict(title="Customized API")

    api_endpoint: ApiEndpointType = ApiEndpointField  # type: ignore (Dynamic type generation)
    api_headers: ApiHeadersType = ApiHeadersField  # type: ignore (Dynamic type generation)
    api_additional_query_params: ApiAdditionalQueryParamsType = (  # type: ignore (Dynamic type generation)
        ApiAdditionalQueryParamsField
    )
    api_additional_body_params: ApiAdditionalBodyParamsType = (  # type: ignore (Dynamic type generation)
        ApiAdditionalBodyParamsField
    )
    api_request_method: ApiRequestMethodType = ApiRequestMethodField  # type: ignore (Dynamic type generation)
    search_engine_mode: SearchEngineMode = Field(
        default=SearchEngineMode.STANDARD,
        title="Search Engine Mode",
        description="Whether this custom API behaves as a standard search engine or an agent-based one.",
    )
    requires_scraping: bool = Field(
        default=False, description="Whether the search engine requires scraping"
    )
    timeout: int = Field(default=120, description="The timeout of the custom API")

    @model_validator(mode="before")
    @classmethod
    def reject_operator_config_overrides(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        operator_values = {
            "apiEndpoint": env_settings.custom_web_search_api_endpoint,
            "apiHeaders": env_settings.custom_web_search_api_headers,
            "apiAdditionalQueryParams": (
                env_settings.custom_web_search_api_additional_query_params
            ),
            "apiAdditionalBodyParams": (
                env_settings.custom_web_search_api_additional_body_params
            ),
            "apiRequestMethod": env_settings.custom_web_search_api_method,
        }
        aliases = {
            "apiEndpoint": "api_endpoint",
            "apiHeaders": "api_headers",
            "apiAdditionalQueryParams": "api_additional_query_params",
            "apiAdditionalBodyParams": "api_additional_body_params",
            "apiRequestMethod": "api_request_method",
        }
        for alias, operator_value in operator_values.items():
            if operator_value is None:
                continue
            supplied_value = value.get(alias, value.get(aliases[alias], operator_value))
            if supplied_value != operator_value:
                raise ValueError(f"{alias} is managed by the deployment")
        return value

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        """Use the proxy's wire contract, excluding tool-only configuration fields."""
        return CustomApiSearchRequest


@register_search_engine(
    name="custom_api",
    key=LocalSearchEngineType.CUSTOM_API,
    config_cls=CustomAPIConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="Customized API",
)
class CustomAPI(SearchEngine[CustomAPIConfig]):
    def __init__(
        self,
        config: CustomAPIConfig,
        *,
        request_context: RequestContext = LOCAL_REQUEST_CONTEXT,
    ):
        super().__init__(config, request_context=request_context)
        self.api_endpoint = config.api_endpoint
        self.is_configured = True  # No possibility to check if the API is configured from our side. So we assume it is configured.

    async def _proxy_routing_enabled(self) -> bool:
        return await is_flag_enabled(
            FeatureFlagNames.enable_custom_api_search_proxy_un_26736,
            company_id=self._request_context.company_id,
            user_id=self._request_context.user_id,
        )

    @property
    def _standard_proxy_client_timeout(self) -> float:
        return float(self.config.timeout) + 5.0

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
    ) -> list[WebSearchResult]:
        del params
        await self._report_url_safety()
        params_dict, body = self._prepare_request_params_and_body(query)
        async_client_params: dict[str, Any] = dict(self._client_config)
        async_client_params["timeout"] = self.config.timeout
        async with AsyncClient(**async_client_params) as client:
            response = await client.request(
                method=self._request_method,
                headers=self._headers,
                url=self.api_endpoint,
                params=params_dict,
                json=body,
            )

        if not response.is_success:
            raise ValueError(
                f"Search engine request failed with status {response.status_code}: {response.text}"
            )

        validated_response = WebSearchResults.model_validate(response.json())
        return validated_response.results

    async def _report_url_safety(self) -> None:
        try:
            await UrlSafetyService.resolve_custom_api_target(
                self.config.api_endpoint,
                trusted_private_hosts=(
                    env_settings.custom_web_search_api_trusted_private_hosts
                ),
            )
        except CrawlTargetValidationError as exc:
            reason_category = exc.blocked_targets[0].category
            custom_api_url_safety_report.labels(
                outcome="would_block",
                reason_category=reason_category,
            ).inc()
            _LOGGER.warning(
                "Search Proxy URL safety would block this Custom API endpoint; "
                "continuing through the legacy direct path because proxy routing "
                "is disabled company_id=%s category=%s",
                self._request_context.company_id,
                reason_category,
            )
        except Exception as exc:
            custom_api_url_safety_report.labels(
                outcome="validation_error",
                reason_category="unexpected",
            ).inc()
            _LOGGER.warning(
                "Custom API URL safety report failed company_id=%s error_type=%s",
                self._request_context.company_id,
                type(exc).__name__,
            )
        else:
            custom_api_url_safety_report.labels(
                outcome="allowed",
                reason_category="none",
            ).inc()

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
