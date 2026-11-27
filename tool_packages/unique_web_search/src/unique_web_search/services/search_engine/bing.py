import asyncio
from collections.abc import Sequence
from typing import Any, override

from pydantic import Field
from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.bing.grounding import (
    BingGroundingConfiguration,
)
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentConfig
from unique_search_proxy_core.agent_engines.bing.settings import resolve_market
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.schema import AnswerSpanCitation

from unique_web_search.metrics import (
    grounding_dropped_citations,
    grounding_dropped_lines,
    grounding_parse_failures,
)
from unique_web_search.services.proxy.bridge import (
    search_proxy_client_enabled,
)
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.utils.grounding.bing import (
    BingCitationParser,
    create_and_process_run,
    credentials_are_valid,
    get_credentials,
    get_project_client,
)


class BingSearchConfig(BingAgentConfig):
    requires_scraping: bool = Field(
        default=False,
        description="Whether the search engine requires scraping.",
    )


@register_search_engine(
    name="bing",
    key=AgentEngineType.BING,
    config_cls=BingSearchConfig,
    mode=SearchEngineMode.AGENT,
    config_display_name="Grounding with Bing",
)
class BingSearch(SearchEngine[BingSearchConfig]):
    def __init__(
        self,
        config: BingSearchConfig,
        *,
        request_context: RequestContext = LOCAL_REQUEST_CONTEXT,
    ):
        super().__init__(config, request_context=request_context)
        self.credentials = get_credentials()
        self.citation_response_parser = BingCitationParser()

    @property
    def is_configured(self) -> bool:
        if search_proxy_client_enabled:
            return True

        async def _is_configured() -> bool:
            return await credentials_are_valid(self.credentials)

        return asyncio.run(_is_configured())

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    def _grounding_configuration(self) -> BingGroundingConfiguration:
        """The Bing tool knobs this space has fixed, with the market resolved."""
        return BingGroundingConfiguration(
            fetch_size=self.config.fetch_size,
            market=resolve_market(self.config.market),
            freshness=self.config.freshness,
        )

    @override
    def _agent_proxy_invocation(
        self,
        engine: AgentEngineType,
        params: ExposedParams | None,
    ) -> dict[str, Any]:
        """Resolve the market here too, so the env default works on either service."""
        invocation = super()._agent_proxy_invocation(engine, params)
        market = resolve_market(invocation.get("market"))
        if market is not None:
            invocation["market"] = market
        return invocation

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
    ) -> list[WebSearchResult]:
        agent_client = get_project_client(self.credentials)

        async with agent_client:
            answer, citations = await create_and_process_run(
                agent_client,
                query=query,
                grounding=self._grounding_configuration(),
                generation_instructions=self.config.generation_instructions,
            )

        return await self._parse_agent_answer(answer, citations)

    @override
    async def _parse_agent_answer(
        self,
        answer: str,
        citations: Sequence[AnswerSpanCitation],
    ) -> list[WebSearchResult]:
        parsed = await self.citation_response_parser(answer, citations)
        engine = self.config.engine.value
        for reason, count in parsed.dropped_citations.items():
            grounding_dropped_citations.labels(engine=engine, reason=reason.value).inc(
                count
            )
        for reason, count in parsed.dropped_lines.items():
            grounding_dropped_lines.labels(engine=engine, reason=reason.value).inc(
                count
            )
        if parsed.failure is not None:
            grounding_parse_failures.labels(
                engine=engine, reason=parsed.failure.value
            ).inc()
        return parsed.results
