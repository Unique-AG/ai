"""Facade over the OpenAPI-generated HTTP client (``sdk._generated``).

Regenerate the low-level client with::

    uv run poe generate-sdk
"""

from __future__ import annotations

from typing import Any, cast

import httpx

from unique_search_proxy.sdk._generated.api.configuration import (
    crawler_config_schema_v1_configuration_crawlers_crawler_id_json_schema_get,
    crawler_default_config_v1_configuration_crawlers_crawler_id_default_config_get,
    crawlers_config_schema_v1_configuration_crawlers_json_schema_get,
    list_providers_v1_configuration_providers_get,
    search_engine_call_schema_v1_configuration_search_engines_engine_id_call_schema_post,
    search_engine_config_schema_v1_configuration_search_engines_engine_id_json_schema_get,
    search_engine_default_config_v1_configuration_search_engines_engine_id_default_config_get,
    search_engines_config_schema_v1_configuration_search_engines_json_schema_get,
)
from unique_search_proxy.sdk._generated.api.crawl import crawl_v1_crawl_post
from unique_search_proxy.sdk._generated.api.health import (
    health_health_get,
    ready_ready_get,
)
from unique_search_proxy.sdk._generated.api.search import search_v1_search_post
from unique_search_proxy.sdk._generated.client import Client as OpenAPIClient
from unique_search_proxy.sdk._generated.models.crawl_request import CrawlRequest
from unique_search_proxy.sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy.sdk._generated.models.google_config_request import (
    GoogleConfigRequest,
)
from unique_search_proxy.sdk._generated.models.provider_default_config_response import (
    ProviderDefaultConfigResponse,
)
from unique_search_proxy.sdk._generated.models.provider_json_schema_response import (
    ProviderJsonSchemaResponse,
)
from unique_search_proxy.sdk._generated.models.providers_list_response import (
    ProvidersListResponse,
)
from unique_search_proxy.sdk._generated.models.search_call_schema_response import (
    SearchCallSchemaResponse,
)
from unique_search_proxy.sdk._generated.models.search_response import SearchResponse
from unique_search_proxy.sdk._http import unwrap_response
from unique_search_proxy.sdk.converters import (
    to_sdk_crawler_config,
    to_sdk_google_config,
    to_sdk_google_config_request,
)
from unique_search_proxy.web.core.crawlers.config_types import CrawlerConfigTypes
from unique_search_proxy.web.core.search_engines.base import SearchEngineType
from unique_search_proxy.web.core.search_engines.config_types import (
    SearchEngineConfigTypes,
)
from unique_search_proxy.web.core.search_engines.google.schema import (
    GoogleConfig,
    GoogleSearchRequest,
)

_DEFAULT_TIMEOUT_SECONDS = 60.0


class UniqueSearchProxyClient:
    """Async HTTP client for the search proxy API.

    Wraps :class:`~unique_search_proxy.sdk._generated.client.Client` (from
    ``openapi-python-client``) with proxy-specific error mapping and helpers that
    accept application Pydantic config types.

    **SDK:** caller → proxy HTTP API. **Application:** ``unique_search_proxy.web``.
    """

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._openapi = OpenAPIClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
        )
        if http_client is not None:
            self._openapi.set_async_httpx_client(http_client)

    @property
    def openapi(self) -> OpenAPIClient:
        """Low-level client generated from OpenAPI (one function per route)."""
        return self._openapi

    async def aclose(self) -> None:
        if self._owns_client:
            await self._openapi.get_async_httpx_client().aclose()

    async def __aenter__(self) -> UniqueSearchProxyClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def health(self) -> dict[str, Any]:
        response = await health_health_get.asyncio_detailed(client=self._openapi)
        body = unwrap_response(response)
        return body.to_dict()

    async def ready(self) -> dict[str, Any]:
        response = await ready_ready_get.asyncio_detailed(client=self._openapi)
        body = unwrap_response(response)
        return body.to_dict()

    async def list_providers(self) -> ProvidersListResponse:
        response = await list_providers_v1_configuration_providers_get.asyncio_detailed(
            client=self._openapi,
        )
        return cast(ProvidersListResponse, unwrap_response(response))

    async def search_engines_config_json_schema(
        self,
    ) -> ProviderJsonSchemaResponse:
        response = await search_engines_config_schema_v1_configuration_search_engines_json_schema_get.asyncio_detailed(
            client=self._openapi,
        )
        return cast(ProviderJsonSchemaResponse, unwrap_response(response))

    async def search_engine_config_json_schema(
        self,
        engine_id: str,
    ) -> ProviderJsonSchemaResponse:
        response = await search_engine_config_schema_v1_configuration_search_engines_engine_id_json_schema_get.asyncio_detailed(
            engine_id=engine_id,
            client=self._openapi,
        )
        return cast(ProviderJsonSchemaResponse, unwrap_response(response))

    async def search_engine_default_config(
        self,
        engine_id: str,
    ) -> ProviderDefaultConfigResponse:
        response = await search_engine_default_config_v1_configuration_search_engines_engine_id_default_config_get.asyncio_detailed(
            engine_id=engine_id,
            client=self._openapi,
        )
        return cast(ProviderDefaultConfigResponse, unwrap_response(response))

    async def crawlers_config_json_schema(self) -> ProviderJsonSchemaResponse:
        response = await crawlers_config_schema_v1_configuration_crawlers_json_schema_get.asyncio_detailed(
            client=self._openapi,
        )
        return cast(ProviderJsonSchemaResponse, unwrap_response(response))

    async def crawler_config_json_schema(
        self,
        crawler_id: str,
    ) -> ProviderJsonSchemaResponse:
        response = await crawler_config_schema_v1_configuration_crawlers_crawler_id_json_schema_get.asyncio_detailed(
            crawler_id=crawler_id,
            client=self._openapi,
        )
        return cast(ProviderJsonSchemaResponse, unwrap_response(response))

    async def crawler_default_config(
        self,
        crawler_id: str,
    ) -> ProviderDefaultConfigResponse:
        response = await crawler_default_config_v1_configuration_crawlers_crawler_id_default_config_get.asyncio_detailed(
            crawler_id=crawler_id,
            client=self._openapi,
        )
        return cast(ProviderDefaultConfigResponse, unwrap_response(response))

    async def search_call_schema(
        self,
        engine_id: str,
        *,
        config: SearchEngineConfigTypes | None = None,
        strict: bool = True,
    ) -> SearchCallSchemaResponse:
        """LLM call JSON Schema derived from a deployment config instance."""
        body = (
            to_sdk_google_config(config)
            if config is not None
            else to_sdk_google_config(GoogleConfig())
        )
        response = await search_engine_call_schema_v1_configuration_search_engines_engine_id_call_schema_post.asyncio_detailed(
            engine_id=engine_id,
            client=self._openapi,
            body=body,
            strict=strict,
        )
        return cast(SearchCallSchemaResponse, unwrap_response(response))

    async def search(self, request: GoogleConfigRequest) -> SearchResponse:
        response = await search_v1_search_post.asyncio_detailed(
            client=self._openapi,
            body=request,
        )
        return cast(SearchResponse, unwrap_response(response))

    async def search_with(
        self,
        *,
        engine: SearchEngineType | str,
        request: GoogleSearchRequest,
        timeout: int | None = None,
    ) -> SearchResponse:
        engine_value = engine.value if isinstance(engine, SearchEngineType) else engine
        sdk_request = to_sdk_google_config_request(request)
        sdk_request.engine = engine_value
        if timeout is not None:
            sdk_request.timeout = timeout
        return await self.search(sdk_request)

    async def crawl(self, request: CrawlRequest) -> CrawlResponse:
        response = await crawl_v1_crawl_post.asyncio_detailed(
            client=self._openapi,
            body=request,
        )
        return cast(CrawlResponse, unwrap_response(response))

    async def crawl_urls(
        self,
        *,
        urls: list[str],
        config: CrawlerConfigTypes,
        parallel: bool = True,
        timeout: int = 30,
        accepted_content_types: list[str] | None = None,
    ) -> CrawlResponse:
        return await self.crawl(
            CrawlRequest(
                urls=urls,
                config=to_sdk_crawler_config(config),
                parallel=parallel,
                timeout=timeout,
                accepted_content_types=accepted_content_types,
            ),
        )


__all__ = ["OpenAPIClient", "UniqueSearchProxyClient"]
