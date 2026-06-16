"""HTTP client for ``POST /v1/search``."""

from __future__ import annotations

from typing import Any

from unique_search_proxy_core.search_engines.brave.schema import BraveSearchRequest
from unique_search_proxy_core.search_engines.config_types import parse_search_request
from unique_search_proxy_core.search_engines.google.schema import GoogleSearchRequest
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexitySearchRequest,
)

from unique_search_proxy_sdk._endpoint import async_post_endpoint
from unique_search_proxy_sdk._generated.api.search import search_v1_search_post
from unique_search_proxy_sdk._generated.models.search_response import SearchResponse
from unique_search_proxy_sdk._transport import OpenapiTransport
from unique_search_proxy_sdk._typed_endpoints import (
    BraveSearchEndpoint,
    GoogleSearchEndpoint,
    PerplexitySearchEndpoint,
)
from unique_search_proxy_sdk.converters import to_sdk_search_request

_SEARCH_PROVIDERS = frozenset({"google", "brave", "perplexity"})


class SearchClient:
    """Execute searches via flat, engine-specific request bodies."""

    google: GoogleSearchEndpoint
    brave: BraveSearchEndpoint
    perplexity: PerplexitySearchEndpoint

    def __init__(self, transport: OpenapiTransport) -> None:
        self._transport = transport
        self.google = GoogleSearchEndpoint(
            async_post_endpoint(
                transport,
                GoogleSearchRequest,
                parse=parse_search_request,
                to_sdk=to_sdk_search_request,
                post=search_v1_search_post.asyncio_detailed,
                response_type=SearchResponse,
            ),
        )
        self.brave = BraveSearchEndpoint(
            async_post_endpoint(
                transport,
                BraveSearchRequest,
                parse=parse_search_request,
                to_sdk=to_sdk_search_request,
                post=search_v1_search_post.asyncio_detailed,
                response_type=SearchResponse,
            ),
        )
        self.perplexity = PerplexitySearchEndpoint(
            async_post_endpoint(
                transport,
                PerplexitySearchRequest,
                parse=parse_search_request,
                to_sdk=to_sdk_search_request,
                post=search_v1_search_post.asyncio_detailed,
                response_type=SearchResponse,
            ),
        )

    async def search(
        self,
        query: str,
        *,
        engine: str = "google",
        **params: Any,
    ) -> SearchResponse:
        """Run a search with a flat body validated by core request models."""
        if engine not in _SEARCH_PROVIDERS:
            msg = f"Unknown search engine {engine!r}; expected one of {sorted(_SEARCH_PROVIDERS)}"
            raise ValueError(msg)
        provider = getattr(self, engine)
        return await provider(query=query, **params)


__all__ = ["SearchClient"]
