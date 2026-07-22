from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentSearchRequest
from unique_search_proxy_core.agent_engines.resolve import (
    resolve_output_schema_for_engine,
)
from unique_search_proxy_core.errors import UpstreamError
from unique_search_proxy_core.schema import (
    AgentSearchDelta,
    AgentSearchDone,
    AgentSearchResponse,
    AgentSearchStreamEvent,
)

from unique_search_proxy_client.web.core.agent_engines.bing.client import (
    get_credentials,
    get_project_client,
)
from unique_search_proxy_client.web.core.agent_engines.bing.runner import (
    stream_bing_grounding_agent,
)
from unique_search_proxy_client.web.core.agent_engines.service_base import (
    AgentSearchEngineService,
)
from unique_search_proxy_client.web.core.agent_engines.structured_output import (
    build_agent_instructions,
)
from unique_search_proxy_client.web.core.provider_response import transport_error_raw
from unique_search_proxy_client.web.settings.providers.bing_agent import (
    bing_agent_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import read_secret

_LOGGER = logging.getLogger(__name__)


class BingAgentSearchService(AgentSearchEngineService[BingAgentSearchRequest]):
    engine_id = AgentEngineType.BING.value

    async def search(self, request: BingAgentSearchRequest) -> AgentSearchResponse:  # type: ignore[override]
        response: AgentSearchResponse | None = None
        async for event in self.stream(request):
            if isinstance(event, AgentSearchDone):
                response = event.response
        if response is None:
            msg = "Bing agent search stream ended without a done event"
            raise UpstreamError(msg)
        return response

    async def stream(
        self,
        request: BingAgentSearchRequest,  # type: ignore[override]
    ) -> AsyncIterator[AgentSearchStreamEvent]:
        bing_agent_credentials.check_credentials()
        creds = bing_agent_credentials
        resolved_agent_name = request.agent_id or creds.agent_id

        answer_parts: list[str] = []
        raw_chunks: list[Any] = []

        try:
            project_client = get_project_client(
                get_credentials(),
                endpoint=read_secret(creds.endpoint),
            )
            output_schema = resolve_output_schema_for_engine(request.engine)
            instructions = build_agent_instructions(
                generation_instructions=request.generation_instructions,
                output_schema=output_schema,
            )
            async with project_client:
                async for delta, raw_event in stream_bing_grounding_agent(
                    project_client,
                    query=request.query,
                    model=read_secret(creds.bing_agent_model),
                    fetch_size=request.fetch_size,
                    instructions=instructions,
                    agent_name=resolved_agent_name,
                ):
                    if delta:
                        answer_parts.append(delta)
                        yield AgentSearchDelta(text=delta)
                    if raw_event:
                        raw_chunks.append(raw_event)
        except Exception as exc:
            raise UpstreamError(
                f"Bing agent search failed: {exc}",
                upstream_raw=transport_error_raw(exc),
            ) from exc

        answer = "".join(answer_parts)
        response = AgentSearchResponse(
            engine=AgentEngineType.BING.value,
            query=request.query,
            answer=answer,
            raw=raw_chunks if len(raw_chunks) != 1 else raw_chunks[0],
        )
        yield AgentSearchDone(response=response)
