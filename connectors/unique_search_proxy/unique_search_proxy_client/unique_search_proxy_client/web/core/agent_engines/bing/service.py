from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import openai
from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.bing.grounding import (
    BingGroundingConfiguration,
)
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentSearchRequest
from unique_search_proxy_core.agent_engines.bing.settings import resolve_market
from unique_search_proxy_core.errors import UpstreamError
from unique_search_proxy_core.schema import (
    AgentSearchDelta,
    AgentSearchDone,
    AgentSearchResponse,
    AgentSearchStreamEvent,
    AnswerSpanCitation,
)

from unique_search_proxy_client.web.core.agent_engines.bing.client import (
    bing_azure_transport,
    get_credentials,
    get_project_client,
)
from unique_search_proxy_client.web.core.agent_engines.bing.instructions import (
    build_bing_citation_instructions,
)
from unique_search_proxy_client.web.core.agent_engines.bing.runner import (
    stream_bing_grounding_agent,
)
from unique_search_proxy_client.web.core.agent_engines.service_base import (
    AgentSearchEngineService,
)
from unique_search_proxy_client.web.core.provider_response import transport_error_raw
from unique_search_proxy_client.web.settings.providers.bing_agent import (
    bing_agent_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import read_secret

if TYPE_CHECKING:
    from httpx import AsyncClient
    from unique_search_proxy_core.http_client import EgressRoute

_LOGGER = logging.getLogger(__name__)
# Foundry can report transient backend failures inside an HTTP 200 SSE stream,
# beyond the reach of the OpenAI client's HTTP retry policy.
_RETRYABLE_STREAM_ERROR_CODES = frozenset({"server_error", "internal_error"})
_RETRYABLE_STREAM_ERROR_MESSAGES = (
    "model deployment encountered an error processing your request",
    "invalid or expired token",
)
_STREAM_RETRY_DELAYS_SECONDS = (2.0, 8.0)
_STREAM_MAX_ATTEMPTS = len(_STREAM_RETRY_DELAYS_SECONDS) + 1


def _is_retryable_bing_stream_error(exc: BaseException) -> bool:
    """Return whether a pre-output Foundry stream failure is safe to retry."""
    if isinstance(exc, openai.APIStatusError):
        # The OpenAI client already retries retryable HTTP statuses. This
        # classifier is only for errors embedded in an HTTP 200 SSE stream.
        return False
    if not isinstance(exc, openai.APIError):
        return False

    code = exc.code.lower() if isinstance(exc.code, str) else None
    if code in _RETRYABLE_STREAM_ERROR_CODES:
        return True

    message = str(exc).lower()
    return any(marker in message for marker in _RETRYABLE_STREAM_ERROR_MESSAGES)


class BingAgentSearchService(AgentSearchEngineService[BingAgentSearchRequest]):
    engine_id = AgentEngineType.BING.value

    def __init__(
        self,
        *,
        http_client: AsyncClient,
        egress_route: EgressRoute,
    ) -> None:
        super().__init__(http_client=http_client)
        self._egress_route = egress_route

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
        if http_client is None:
            raise RuntimeError("HTTP client is required for Bing")

        answer_parts: list[str] = []
        completed_answer: str | None = None
        raw_chunks: list[dict] = []
        citations: list[AnswerSpanCitation] = []

        instructions = build_bing_citation_instructions(
            request.generation_instructions,
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
                            async for chunk in stream_bing_grounding_agent(
                                project_client,
                                http_client=http_client,
                                query=request.query,
                                model=read_secret(creds.bing_agent_model),
                                instructions=instructions,
                                grounding=grounding,
                                timeout=request.timeout,
                            ):
                                if chunk.delta:
                                    answer_parts.append(chunk.delta)
                                    yield AgentSearchDelta(text=chunk.delta)
                                if chunk.raw_event:
                                    raw_chunks.append(chunk.raw_event)
                                if chunk.answer is not None:
                                    completed_answer = chunk.answer
                                    citations = list(chunk.citations)
                break
            except Exception as exc:
                retryable = (
                    attempt < _STREAM_MAX_ATTEMPTS
                    and not answer_parts
                    and _is_retryable_bing_stream_error(exc)
                )
                if not retryable:
                    raise UpstreamError(
                        f"Bing agent search failed: {exc}",
                        upstream_raw=transport_error_raw(exc),
                    ) from exc

                raw_chunks.clear()
                completed_answer = None
                citations = []
                retry_delay = _STREAM_RETRY_DELAYS_SECONDS[attempt - 1]
                _LOGGER.warning(
                    "Bing response failed before output; retrying attempt %d/%d "
                    "after %.1fs (type=%s, code=%s)",
                    attempt + 1,
                    _STREAM_MAX_ATTEMPTS,
                    retry_delay,
                    type(exc).__name__,
                    getattr(exc, "code", None),
                )
                await asyncio.sleep(retry_delay)

        answer = (
            completed_answer if completed_answer is not None else "".join(answer_parts)
        )
        response = AgentSearchResponse(
            engine=AgentEngineType.BING.value,
            query=request.query,
            answer=answer,
            citations=citations,
            raw=raw_chunks if len(raw_chunks) != 1 else raw_chunks[0],
        )
        yield AgentSearchDone(response=response)
