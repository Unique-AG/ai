import asyncio
import logging
from typing import override

from httpx import AsyncClient as HttpxAsyncClient
from httpx import HTTPError
from pydantic import Field
from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.vertexai.schema import VertexAIAgentConfig
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_toolkit._common.default_language_model import DEFAULT_LANGUAGE_MODEL
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.language_model import LanguageModelService

from unique_web_search.services.proxy.bridge import (
    search_proxy_client_enabled,
)
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)
from unique_web_search.services.search_engine.utils.grounding import (
    JsonConversionStrategy,
    LLMParserStrategy,
    convert_response_to_search_results,
)
from unique_web_search.services.search_engine.utils.grounding.vertexai import (
    add_citations,
    generate_vertexai_response,
    get_vertex_client,
    get_vertex_grounding_with_structured_output_config,
)

_LOGGER = logging.getLogger(__name__)


class VertexAIConfig(VertexAIAgentConfig):
    language_model: LMI = get_LMI_default_field(
        DEFAULT_LANGUAGE_MODEL,
        description="The language model to use as a fallback parser if the grounding response is not valid JSON.",
    )

    requires_scraping: bool = Field(
        default=False,
        description="Whether the search engine requires scraping.",
    )

    enable_redirect_resolution: bool = Field(
        default=True,
        description="Whether to enable redirect resolution.",
    )


@register_search_engine(
    name="vertexai",
    key=AgentEngineType.VERTEXAI,
    config_cls=VertexAIConfig,
    mode=SearchEngineMode.AGENT,
    config_display_name="Grounding with VertexAI",
    needs_language_model=True,
)
class VertexAI(SearchEngine[VertexAIConfig]):
    def __init__(
        self,
        config: VertexAIConfig,
        language_model_service: LanguageModelService,
        *,
        request_context: RequestContext = LOCAL_REQUEST_CONTEXT,
    ):
        super().__init__(config=config, request_context=request_context)
        self._client = get_vertex_client()
        self.is_configured = search_proxy_client_enabled or self._client is not None

        self.response_parsers = [
            JsonConversionStrategy(),
            LLMParserStrategy(
                config.language_model,
                language_model_service,
            ),
        ]

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    @override
    async def _postprocess_results(
        self,
        results: list[WebSearchResult],
    ) -> list[WebSearchResult]:
        if self.config.enable_redirect_resolution:
            resolved = await resolve_all(WebSearchResults(results=results))
            return resolved.results
        return results

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
        *,
        invocation_stats=None,
    ) -> list[WebSearchResult]:
        del params
        assert self._client is not None, "VertexAI client is not configured"

        response = await generate_vertexai_response(
            client=self._client,
            model_name=self.config.vertexai_model_name,
            config=get_vertex_grounding_with_structured_output_config(
                generation_instructions=self.config.generation_instructions,
                entreprise_search=self.config.enable_enterprise_search,
            ),
            contents=query,
        )

        answer_with_citations = add_citations(response)

        results = await convert_response_to_search_results(
            answer_with_citations, self._response_parsers_for(invocation_stats)
        )

        return await self._postprocess_results(results)


async def resolve_url(client: HttpxAsyncClient, web_search_result: WebSearchResult):
    try:
        resp = await client.head(web_search_result.url, follow_redirects=True)
        web_search_result.url = str(resp.url)
        return web_search_result
    except HTTPError as e:
        _LOGGER.error(f"Unable to redirect URL: {web_search_result.url}: {e}")
        return web_search_result


async def resolve_all(web_search_results: WebSearchResults):
    async with HttpxAsyncClient(follow_redirects=True, timeout=10) as client:
        tasks = [resolve_url(client, result) for result in web_search_results.results]
        results = await asyncio.gather(*tasks)
        return WebSearchResults(results=results)
