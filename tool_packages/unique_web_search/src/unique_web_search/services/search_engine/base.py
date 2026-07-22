from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel
from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.config_types import ENGINE_NAME_TO_CONFIG
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats

from unique_web_search.services.proxy.bridge import (
    open_search_proxy_client,
    search_proxy_client_enabled,
)
from unique_web_search.services.proxy.mappers import (
    agent_answer_text,
    map_agent_answer,
    map_search_response,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

if TYPE_CHECKING:
    from unique_web_search.services.search_engine.utils.grounding.response_parsing import (
        ResponseParser,
    )


class SearchEngineMode(StrEnum):
    STANDARD = "standard"
    AGENT = "agent"


class LocalSearchEngineType(StrEnum):
    CUSTOM_API = "custom_api"


# Engine ids that the search proxy can serve. Every other engine
# (e.g. ``LocalSearchEngineType``) is routed to the local legacy implementation.
ProxyEngineType = SearchEngineType | AgentEngineType

# Fields present on agent-engine configs that are not accepted as proxy call kwargs.
_AGENT_PROXY_EXCLUDED_FIELDS = frozenset({"engine", "output_schema"})

# Standard proxy client timeout (seconds); agent engines use ``config.timeout``.
_STANDARD_PROXY_TIMEOUT = 30.0

SearchEngineConfig = TypeVar(
    "SearchEngineConfig",
    bound=BaseModel,
)


class SearchEngine(ABC, Generic[SearchEngineConfig]):
    """Base class for the search engine.

    The search-proxy path (both standard engines like Google/Brave/Perplexity and
    agent engines like Bing/VertexAI) is implemented entirely here. Subclasses only
    provide the direct ``_legacy_search`` implementation.

    ``search`` uses the proxy whenever it is enabled and the engine is supported by
    it, otherwise it reroutes to the local legacy implementation. Engines that the
    proxy cannot serve (e.g. custom APIs) always fall back to ``_legacy_search``.
    """

    # Set by agent engines (Bing/VertexAI) and consumed by the agent proxy path.
    response_parsers: list[ResponseParser]

    def __init__(
        self,
        config: SearchEngineConfig,
        *,
        request_context: RequestContext = LOCAL_REQUEST_CONTEXT,
    ):
        self.config = config
        self._request_context = request_context

    @property
    def requires_scraping(self) -> bool:
        """Whether the search engine requires scraping."""
        return False

    @property
    def _proxy_engine(self) -> ProxyEngineType | None:
        """The proxy engine id for this config, or ``None`` if not proxy-supported."""
        engine = getattr(self.config, "engine", None)
        if isinstance(engine, (SearchEngineType, AgentEngineType)):
            return engine
        return None

    def _response_parsers_for(
        self,
        invocation_stats: list[LanguageModelInvocationStats] | None,
    ) -> list[ResponseParser]:
        """Clone agent parsers so LLM fallback usage can bind to a run-scoped list."""
        parsers = getattr(self, "response_parsers", None)
        if not parsers:
            return []
        if invocation_stats is None:
            return list(parsers)
        return [
            parser.with_invocation_stats(invocation_stats)
            if hasattr(parser, "with_invocation_stats")
            else parser
            for parser in parsers
        ]

    async def search(
        self,
        query: str,
        params: ExposedParams | None = None,
        *,
        invocation_stats: list[LanguageModelInvocationStats] | None = None,
    ) -> list[WebSearchResult]:
        """Search the web for the given query using the search engine."""
        proxy_engine = self._proxy_engine
        if search_proxy_client_enabled and proxy_engine is not None:
            return await self._proxy_search(
                query, params, proxy_engine, invocation_stats=invocation_stats
            )
        return await self._legacy_search(
            query=query, params=params, invocation_stats=invocation_stats
        )

    async def _proxy_search(
        self,
        query: str,
        params: ExposedParams | None,
        engine: ProxyEngineType,
        *,
        invocation_stats: list[LanguageModelInvocationStats] | None = None,
    ) -> list[WebSearchResult]:
        """Dispatch to the appropriate proxy path for the given engine."""
        if isinstance(engine, AgentEngineType):
            return await self._agent_proxy_search(
                query, params, engine, invocation_stats=invocation_stats
            )
        return await self._standard_proxy_search(query, params, engine)

    async def _standard_proxy_search(
        self,
        query: str,
        params: ExposedParams | None,
        engine: SearchEngineType,
    ) -> list[WebSearchResult]:
        """Merge deployment config with per-call params and dispatch via the proxy SDK."""
        if not isinstance(self.config, BaseSearchEngineConfig):
            raise TypeError(
                f"Standard proxy search requires BaseSearchEngineConfig, "
                f"got {type(self.config).__name__}"
            )
        overrides = (
            params.model_dump(by_alias=True, exclude_none=True) if params else {}
        )
        request = self.config.merge(overrides, query=query)
        invocation = request.model_dump(by_alias=False, exclude_none=True)
        invocation.pop("engine", None)
        invocation.pop("query", None)
        async with open_search_proxy_client(
            timeout=_STANDARD_PROXY_TIMEOUT,
            context=self._request_context,
        ) as client:
            response = await client.search.search(
                query=query,
                engine=engine.value,
                **invocation,
            )
        results = map_search_response(response)
        return await self._postprocess_results(results)

    async def _agent_proxy_search(
        self,
        query: str,
        params: ExposedParams | None,
        engine: AgentEngineType,
        *,
        invocation_stats: list[LanguageModelInvocationStats] | None = None,
    ) -> list[WebSearchResult]:
        """Dispatch a grounded agent search via the proxy SDK and parse the answer."""
        del params  # Agent engines do not expose LLM knobs today.
        invocation = self._agent_proxy_invocation(engine)
        async with open_search_proxy_client(
            timeout=float(self.config.timeout),
            context=self._request_context,
        ) as client:
            response = await client.agent_search.search(
                query=query,
                engine=engine.value,
                **invocation,
            )
        results = await map_agent_answer(
            agent_answer_text(response),
            self._response_parsers_for(invocation_stats),
        )
        return await self._postprocess_results(results)

    def _agent_proxy_invocation(self, engine: AgentEngineType) -> dict[str, Any]:
        """Collect the config fields accepted by the agent proxy call for ``engine``."""
        core_config_cls = ENGINE_NAME_TO_CONFIG[engine.value]
        invocation: dict[str, Any] = {}
        for field_name in core_config_cls.model_fields:
            if field_name in _AGENT_PROXY_EXCLUDED_FIELDS:
                continue
            if not hasattr(self.config, field_name):
                continue
            value = getattr(self.config, field_name)
            # Empty values fall through to the SDK/server defaults (e.g. an unset
            # ``agent_id`` triggers server-side auto-provisioning).
            if value == "":
                continue
            invocation[field_name] = value
        return invocation

    async def _postprocess_results(
        self,
        results: list[WebSearchResult],
    ) -> list[WebSearchResult]:
        """Hook for engine-specific result shaping shared by proxy and legacy paths."""
        return results

    @abstractmethod
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
        *,
        invocation_stats: list[LanguageModelInvocationStats] | None = None,
    ) -> list[WebSearchResult]:
        """Search the web directly without the search proxy."""
