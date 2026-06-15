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
    run_bing_grounding_agent,
)
from unique_search_proxy_client.web.core.agent_engines.service_base import (
    AgentSearchEngineService,
)
from unique_search_proxy_client.web.core.provider_response import transport_error_raw
from unique_search_proxy_client.web.settings.providers.bing_agent import (
    bing_agent_credentials,
)

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
        resolved_agent_id = request.agent_id or creds.agent_id

        try:
            agent_client = get_project_client(
                get_credentials(),
                endpoint=creds.endpoint,
            )
            output_schema = resolve_output_schema_for_engine(request.engine)
            async with agent_client:
                answer, raw = await run_bing_grounding_agent(
                    agent_client,
                    agent_id=resolved_agent_id,
                    query=request.query,
                    fetch_size=request.fetch_size,
                    generation_instructions=request.generation_instructions,
                    output_schema=output_schema,
                )
        except Exception as exc:
            raise UpstreamError(
                f"Bing agent search failed: {exc}",
                upstream_raw=transport_error_raw(exc),
            ) from exc

        response = _build_response(request, answer=answer, raw=raw)
        if answer:
            yield AgentSearchDelta(text=answer)
        yield AgentSearchDone(response=response)


def _build_response(
    request: BingAgentSearchRequest,
    *,
    answer: str,
    raw: Any,
) -> AgentSearchResponse:
    return AgentSearchResponse(
        engine=AgentEngineType.BING.value,
        query=request.query,
        answer=answer,
        raw=raw,
    )
