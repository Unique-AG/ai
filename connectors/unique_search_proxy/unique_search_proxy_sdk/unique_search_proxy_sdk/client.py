"""Facade composing search and crawl HTTP clients.

Regenerate the low-level client with::

    uv run poe generate-sdk

Schema operations (config resolution, LLM call-schema projection) live in
``unique_search_proxy_core`` — not in this SDK.
"""

from __future__ import annotations

import httpx

from unique_search_proxy_sdk._generated.client import Client as OpenAPIClient
from unique_search_proxy_sdk._transport import OpenapiTransport
from unique_search_proxy_sdk.agent_search_client import AgentSearchClient
from unique_search_proxy_sdk.crawl_client import CrawlClient
from unique_search_proxy_sdk.search_client import SearchClient

_DEFAULT_TIMEOUT_SECONDS = 60.0


class UniqueSearchProxyClient:
    """Async HTTP entrypoint for the search proxy API.

    Exposes :attr:`search`, :attr:`agent_search`, and :attr:`crawl` sub-clients.
    Configuration and call-schema helpers belong in ``unique_search_proxy_core``.
    """

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._transport = OpenapiTransport(
            base_url,
            http_client=http_client,
            timeout=timeout,
        )
        self.search = SearchClient(self._transport)
        self.agent_search = AgentSearchClient(self._transport)
        self.crawl = CrawlClient(self._transport)

    @property
    def openapi(self) -> OpenAPIClient:
        """Low-level client generated from OpenAPI (one function per route)."""
        return self._transport.openapi

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> UniqueSearchProxyClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def health(self) -> dict[str, object]:
        return await self._transport.health()

    async def ready(self) -> dict[str, object]:
        return await self._transport.ready()


__all__ = ["OpenAPIClient", "UniqueSearchProxyClient"]
