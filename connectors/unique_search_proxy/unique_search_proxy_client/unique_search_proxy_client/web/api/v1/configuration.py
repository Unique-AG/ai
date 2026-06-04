"""Provider configuration discovery for admin UI and assistants-core manifests."""

from __future__ import annotations

from fastapi import APIRouter, Body, Query
from unique_search_proxy_core.errors import ValidationProxyError
from unique_search_proxy_core.search_engines.config_types import (
    SearchEngineConfigTypes,
)

from unique_search_proxy_client.web.api.v1.openapi_examples import (
    SEARCH_ENGINE_CALL_SCHEMA_OPENAPI_EXAMPLES,
)
from unique_search_proxy_client.web.api.v1.schema import (
    ProviderDefaultConfigResponse,
    ProviderJsonSchemaResponse,
    ProvidersListResponse,
    SearchCallSchemaResponse,
)
from unique_search_proxy_client.web.core.provider_config_schema import (
    list_registered_providers,
    provider_config_json_schema,
    provider_default_config,
    registered_crawlers_config_json_schema,
    registered_search_engines_config_json_schema,
)
from unique_search_proxy_client.web.core.search_engines.call_schema import (
    resolve_search_call_schema,
)

router = APIRouter(prefix="/configuration", tags=["configuration"])


@router.get(
    "/providers",
    response_model=ProvidersListResponse,
    summary="List registered search engines and crawlers",
)
async def list_providers() -> ProvidersListResponse:
    providers = list_registered_providers()
    return ProvidersListResponse(
        search_engines=providers["search_engines"],
        crawlers=providers["crawlers"],
    )


@router.get(
    "/search-engines/json-schema",
    response_model=ProviderJsonSchemaResponse,
    summary="JSON Schema for search-engine config (discriminated union)",
)
async def search_engines_config_schema() -> ProviderJsonSchemaResponse:
    return ProviderJsonSchemaResponse(
        json_schema=registered_search_engines_config_json_schema(),
    )


@router.get(
    "/search-engines/{engine_id}/json-schema",
    response_model=ProviderJsonSchemaResponse,
    summary="JSON Schema for one search-engine config",
)
async def search_engine_config_schema(engine_id: str) -> ProviderJsonSchemaResponse:
    return ProviderJsonSchemaResponse(
        provider_id=engine_id.lower(),
        json_schema=provider_config_json_schema("search_engine", engine_id),
    )


@router.get(
    "/search-engines/{engine_id}/default-config",
    response_model=ProviderDefaultConfigResponse,
    summary="Default deployment config for one search engine",
)
async def search_engine_default_config(
    engine_id: str,
) -> ProviderDefaultConfigResponse:
    return ProviderDefaultConfigResponse(
        provider_id=engine_id.lower(),
        default_config=provider_default_config("search_engine", engine_id),
    )


@router.post(
    "/search-engines/{engine_id}/call-schema",
    response_model=SearchCallSchemaResponse,
    summary="JSON Schema for POST /v1/search from deployment config",
)
async def search_engine_call_schema(
    engine_id: str,
    config: SearchEngineConfigTypes = Body(
        openapi_examples=SEARCH_ENGINE_CALL_SCHEMA_OPENAPI_EXAMPLES,
    ),
    strict: bool = Query(
        default=True,
        description=(
            "When true (default), the call schema marks every exposed field as required "
            "with no defaults (for strict LLM JSON generation). When false, optional "
            "provider knobs keep nullable types and defaults."
        ),
    ),
) -> SearchCallSchemaResponse:
    if config.engine.value != engine_id.lower():
        raise ValidationProxyError(
            f"Config engine {config.engine.value!r} does not match path {engine_id!r}",
            engine=engine_id,
        )
    descriptor = resolve_search_call_schema(engine_id, config=config, strict=strict)
    return SearchCallSchemaResponse(
        engine=descriptor.engine,
        mode=descriptor.mode,
        snippet_only=descriptor.snippet_only,
        call_schema=descriptor.call_schema,
    )


@router.get(
    "/crawlers/json-schema",
    response_model=ProviderJsonSchemaResponse,
    summary="JSON Schema for crawler config (discriminated union)",
)
async def crawlers_config_schema() -> ProviderJsonSchemaResponse:
    return ProviderJsonSchemaResponse(
        json_schema=registered_crawlers_config_json_schema(),
    )


@router.get(
    "/crawlers/{crawler_id}/json-schema",
    response_model=ProviderJsonSchemaResponse,
    summary="JSON Schema for one crawler config",
)
async def crawler_config_schema(crawler_id: str) -> ProviderJsonSchemaResponse:
    return ProviderJsonSchemaResponse(
        provider_id=crawler_id.lower(),
        json_schema=provider_config_json_schema("crawler", crawler_id),
    )


@router.get(
    "/crawlers/{crawler_id}/default-config",
    response_model=ProviderDefaultConfigResponse,
    summary="Default deployment config for one crawler",
)
async def crawler_default_config(crawler_id: str) -> ProviderDefaultConfigResponse:
    return ProviderDefaultConfigResponse(
        provider_id=crawler_id.lower(),
        default_config=provider_default_config("crawler", crawler_id),
    )


__all__ = ["router"]
