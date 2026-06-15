"""HTTP client for ``POST /v1/agent-search`` and ``/v1/agent-search/stream``."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, cast, overload

import httpx
from unique_search_proxy_core.agent_engines.config_types import (
    parse_agent_search_request,
)

from unique_search_proxy_sdk._generated.api.agent_search import (
    agent_search_v1_agent_search_post,
)
from unique_search_proxy_sdk._generated.models.agent_search_response import (
    AgentSearchResponse,
)
from unique_search_proxy_sdk._http import unwrap_response
from unique_search_proxy_sdk._transport import OpenapiTransport
from unique_search_proxy_sdk.converters import to_sdk_agent_search_request
from unique_search_proxy_sdk.errors import raise_for_proxy_response


class AgentSearchClient:
    """Execute agent-based grounded searches via flat, engine-specific bodies."""

    def __init__(self, transport: OpenapiTransport) -> None:
        self._transport = transport

    @overload
    async def search(
        self,
        query: str,
        *,
        engine: str = "bing",
        **params: Any,
    ) -> AgentSearchResponse: ...

    async def search(
        self,
        query: str,
        *,
        engine: str = "bing",
        **params: Any,
    ) -> AgentSearchResponse:
        payload = {"query": query, "engine": engine, **params}
        validated = parse_agent_search_request(payload)
        sdk_body = to_sdk_agent_search_request(validated)
        response = await agent_search_v1_agent_search_post.asyncio_detailed(
            client=self._transport.openapi,
            body=sdk_body,
        )
        return cast(AgentSearchResponse, unwrap_response(response))

    @overload
    def stream(
        self,
        query: str,
        *,
        engine: str = "bing",
        **params: Any,
    ) -> AsyncIterator[dict[str, Any]]: ...

    async def stream(
        self,
        query: str,
        *,
        engine: str = "bing",
        **params: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed SSE ``data:`` JSON objects (delta / done / error envelope)."""
        payload = {"query": query, "engine": engine, **params}
        validated = parse_agent_search_request(payload)
        sdk_body = to_sdk_agent_search_request(validated)
        http_client = self._transport.openapi.get_async_httpx_client()
        base_url = str(self._transport.openapi.base_url).rstrip("/")
        async with http_client.stream(
            "POST",
            f"{base_url}/v1/agent-search/stream",
            json=sdk_body.to_dict(),
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status_code >= 400:
                raw = await response.aread()
                raise_for_proxy_response(
                    httpx.Response(
                        status_code=response.status_code,
                        content=raw,
                        headers=dict(response.headers),
                    ),
                )
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                yield json.loads(line.removeprefix("data: "))


__all__ = ["AgentSearchClient"]
