from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.resolve import (
    resolve_output_schema_for_engine,
)
from unique_search_proxy_core.agent_engines.vertexai.schema import (
    VertexAIAgentSearchRequest,
)
from unique_search_proxy_core.errors import UpstreamError
from unique_search_proxy_core.schema import (
    AgentSearchDelta,
    AgentSearchDone,
    AgentSearchResponse,
    AgentSearchStreamEvent,
)

from unique_search_proxy_client.web.core.agent_engines.service_base import (
    AgentSearchEngineService,
)
from unique_search_proxy_client.web.core.agent_engines.vertexai.client import (
    get_vertex_client,
)
from unique_search_proxy_client.web.core.agent_engines.vertexai.gemini import (
    build_generate_content_config,
    serialize_vertex_response,
    stream_vertexai_response,
)
from unique_search_proxy_client.web.core.provider_response import transport_error_raw

_LOGGER = logging.getLogger(__name__)


class VertexAIAgentSearchService(
    AgentSearchEngineService[VertexAIAgentSearchRequest],
):
    engine_id = AgentEngineType.VERTEXAI.value

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client = get_vertex_client()

    async def search(self, request: VertexAIAgentSearchRequest) -> AgentSearchResponse:  # type: ignore[override]
        response: AgentSearchResponse | None = None
        async for event in self.stream(request):
            if isinstance(event, AgentSearchDone):
                response = event.response
        if response is None:
            msg = "VertexAI agent search stream ended without a done event"
            raise UpstreamError(msg)
        return response

    async def stream(
        self,
        request: VertexAIAgentSearchRequest,  # type: ignore[override]
    ) -> AsyncIterator[AgentSearchStreamEvent]:
        if self._client is None:
            raise UpstreamError("VertexAI client is not configured")

        output_schema = resolve_output_schema_for_engine(request.engine)
        config = build_generate_content_config(
            generation_instructions=request.generation_instructions,
            output_schema=output_schema,
            enable_enterprise_search=request.enable_enterprise_search,
        )

        answer_parts: list[str] = []
        raw_chunks: list[Any] = []

        try:
            async for chunk in stream_vertexai_response(
                client=self._client,
                model_name=request.vertexai_model_name,
                config=config,
                contents=request.query,
            ):
                text = chunk.text or ""
                if text:
                    answer_parts.append(text)
                    yield AgentSearchDelta(text=text)
                raw_chunks.append(serialize_vertex_response(chunk))
        except Exception as exc:
            raise UpstreamError(
                f"VertexAI agent search failed: {exc}",
                upstream_raw=transport_error_raw(exc),
            ) from exc

        answer = "".join(answer_parts)
        response = AgentSearchResponse(
            engine=AgentEngineType.VERTEXAI.value,
            query=request.query,
            answer=answer,
            raw=raw_chunks if len(raw_chunks) != 1 else raw_chunks[0],
        )
        yield AgentSearchDone(response=response)
