"""HTTP client for ``POST /v1/search``."""

from __future__ import annotations

from typing import Any, Literal, cast, overload

from unique_search_proxy_core.search_engines.config_types import parse_search_request
from unique_search_proxy_core.search_engines.google.schema import (
    GoogleSafeDefault,
    GoogleSiteSearchFilter,
)

from unique_search_proxy_sdk._generated.api.search import search_v1_search_post
from unique_search_proxy_sdk._generated.models.search_response import SearchResponse
from unique_search_proxy_sdk._http import unwrap_response
from unique_search_proxy_sdk._transport import OpenapiTransport
from unique_search_proxy_sdk.converters import to_sdk_search_request


class SearchClient:
    """Execute searches via flat, engine-specific request bodies."""

    def __init__(self, transport: OpenapiTransport) -> None:
        self._transport = transport

    @overload
    async def search(
        self,
        query: str,
        *,
        engine: Literal["google"] = "google",
        fetch_size: int = ...,
        timeout: int = ...,
        search_engine_id: str | None = ...,
        safe: GoogleSafeDefault = ...,
        gl: str | None = ...,
        hl: str | None = ...,
        lr: str | None = ...,
        date_restrict: str | None = ...,
        exact_terms: str | None = ...,
        exclude_terms: str | None = ...,
        file_type: str | None = ...,
        site_search: str | None = ...,
        site_search_filter: GoogleSiteSearchFilter | None = ...,
        sort: str | None = ...,
    ) -> SearchResponse: ...

    @overload
    async def search(
        self,
        query: str,
        *,
        engine: str,
        **params: Any,
    ) -> SearchResponse: ...

    async def search(
        self,
        query: str,
        *,
        engine: str = "google",
        **params: Any,
    ) -> SearchResponse:
        """Run a search with a flat body validated by core request models."""
        payload = {"query": query, "engine": engine, **params}
        validated = parse_search_request(payload)
        sdk_body = to_sdk_search_request(validated)
        response = await search_v1_search_post.asyncio_detailed(
            client=self._transport.openapi,
            body=sdk_body,
        )
        return cast(SearchResponse, unwrap_response(response))


__all__ = ["SearchClient"]
