"""HTTP client for ``POST /v1/agent-search`` and ``/v1/agent-search/stream``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from unique_search_proxy_core.agent_engines.bing.schema import BingAgentSearchRequest
from unique_search_proxy_core.agent_engines.config_types import (
    parse_agent_search_request,
)
from unique_search_proxy_core.agent_engines.vertexai.schema import (
    VertexAIAgentSearchRequest,
)

from unique_search_proxy_sdk._endpoint import async_post_endpoint, async_sse_endpoint
from unique_search_proxy_sdk._generated.api.agent_search import (
    agent_search_v1_agent_search_post,
)
from unique_search_proxy_sdk._generated.models.agent_search_response import (
    AgentSearchResponse,
)
from unique_search_proxy_sdk._transport import OpenapiTransport
from unique_search_proxy_sdk._typed_endpoints import (
    BingAgentSearchEndpoint,
    BingAgentSearchStreamEndpoint,
    VertexAIAgentSearchEndpoint,
    VertexAIAgentSearchStreamEndpoint,
)
from unique_search_proxy_sdk.converters import to_sdk_agent_search_request

_AGENT_PROVIDERS = frozenset({"bing", "vertexai"})


class AgentSearchClient:
    """Execute agent-based grounded searches via flat, engine-specific bodies."""

    bing: BingAgentSearchEndpoint
    vertexai: VertexAIAgentSearchEndpoint
    bing_stream: BingAgentSearchStreamEndpoint
    vertexai_stream: VertexAIAgentSearchStreamEndpoint

    def __init__(self, transport: OpenapiTransport) -> None:
        self._transport = transport
        self.bing = BingAgentSearchEndpoint(
            async_post_endpoint(
                transport,
                BingAgentSearchRequest,
                parse=parse_agent_search_request,
                to_sdk=to_sdk_agent_search_request,
                post=agent_search_v1_agent_search_post.asyncio_detailed,
                response_type=AgentSearchResponse,
            ),
        )
        self.vertexai = VertexAIAgentSearchEndpoint(
            async_post_endpoint(
                transport,
                VertexAIAgentSearchRequest,
                parse=parse_agent_search_request,
                to_sdk=to_sdk_agent_search_request,
                post=agent_search_v1_agent_search_post.asyncio_detailed,
                response_type=AgentSearchResponse,
            ),
        )
        self.bing_stream = BingAgentSearchStreamEndpoint(
            async_sse_endpoint(
                transport,
                "/v1/agent-search/stream",
                BingAgentSearchRequest,
                parse=parse_agent_search_request,
                to_sdk=to_sdk_agent_search_request,
            ),
        )
        self.vertexai_stream = VertexAIAgentSearchStreamEndpoint(
            async_sse_endpoint(
                transport,
                "/v1/agent-search/stream",
                VertexAIAgentSearchRequest,
                parse=parse_agent_search_request,
                to_sdk=to_sdk_agent_search_request,
            ),
        )

    async def search(
        self,
        query: str,
        *,
        engine: str = "bing",
        **params: Any,
    ) -> AgentSearchResponse:
        """Run agent search with a flat body validated by core request models."""
        if engine not in _AGENT_PROVIDERS:
            msg = (
                f"Unknown agent engine {engine!r}; "
                f"expected one of {sorted(_AGENT_PROVIDERS)}"
            )
            raise ValueError(msg)
        provider = getattr(self, engine)
        return await provider(query=query, **params)

    async def stream(
        self,
        query: str,
        *,
        engine: str = "bing",
        **params: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed SSE ``data:`` JSON objects (delta / done / error envelope)."""
        if engine not in _AGENT_PROVIDERS:
            msg = (
                f"Unknown agent engine {engine!r}; "
                f"expected one of {sorted(_AGENT_PROVIDERS)}"
            )
            raise ValueError(msg)
        stream_fn = getattr(self, f"{engine}_stream")
        async for event in stream_fn(query=query, **params):
            yield event


__all__ = ["AgentSearchClient"]
