from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.bing.grounding import (
    BingGroundingConfiguration,
)
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentSearchRequest
from unique_search_proxy_core.agent_engines.bing.settings import resolve_market
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
    bing_azure_transport,
    get_credentials,
    get_project_client,
)
from unique_search_proxy_client.web.core.agent_engines.bing.runner import (
    is_retryable_bing_response_error,
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
# Foundry can report transient backend failures inside an HTTP 200 SSE stream,
# beyond the reach of the OpenAI client's HTTP retry policy.
_STREAM_RETRY_DELAYS_SECONDS = (2.0, 8.0)
_STREAM_MAX_ATTEMPTS = len(_STREAM_RETRY_DELAYS_SECONDS) + 1


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
        http_client = self._http_client
        egress_route = self._egress_route
        if http_client is None or egress_route is None:
            raise RuntimeError("HTTP client and egress route are required for Bing")

        answer_parts: list[str] = []
        raw_chunks: list[dict] = []

        output_schema = resolve_output_schema_for_engine(request.engine)
        instructions = build_agent_instructions(
            generation_instructions=request.generation_instructions,
            output_schema=output_schema,
        )
        grounding = BingGroundingConfiguration(
            fetch_size=request.fetch_size,
            market=resolve_market(request.market),
            freshness=request.freshness,
        )

        for attempt in range(1, _STREAM_MAX_ATTEMPTS + 1):
            try:
                async with bing_azure_transport(egress_route) as azure_transport:
                    async with get_credentials(transport=azure_transport) as credential:
                        async with get_project_client(
                            credential,
                            endpoint=read_secret(creds.endpoint),
                            transport=azure_transport,
                        ) as project_client:
                            async for (
                                delta,
                                raw_event,
                            ) in stream_bing_grounding_agent(
                                project_client,
                                http_client=http_client,
                                query=request.query,
                                model=read_secret(creds.bing_agent_model),
                                instructions=instructions,
                                grounding=grounding,
                                timeout=request.timeout,
                            ):
                                if delta:
                                    answer_parts.append(delta)
                                    yield AgentSearchDelta(text=delta)
                                if raw_event:
                                    raw_chunks.append(raw_event)
                break
            except Exception as exc:
                retryable = (
                    attempt < _STREAM_MAX_ATTEMPTS
                    and not answer_parts
                    and is_retryable_bing_response_error(exc)
                )
                if not retryable:
                    raise UpstreamError(
                        f"Bing agent search failed: {exc}",
                        upstream_raw=transport_error_raw(exc),
                    ) from exc

                raw_chunks.clear()
                retry_delay = _STREAM_RETRY_DELAYS_SECONDS[attempt - 1]
                _LOGGER.warning(
                    "Transient Bing response failure before output; retrying "
                    "attempt %d/%d after %.1fs (type=%s, code=%s)",
                    attempt + 1,
                    _STREAM_MAX_ATTEMPTS,
                    retry_delay,
                    type(exc).__name__,
                    getattr(exc, "code", None),
                )
                await asyncio.sleep(retry_delay)

        answer = "".join(answer_parts)
        response = AgentSearchResponse(
            engine=AgentEngineType.BING.value,
            query=request.query,
            answer=answer,
            raw=raw_chunks if len(raw_chunks) != 1 else raw_chunks[0],
        )
        yield AgentSearchDone(response=response)
