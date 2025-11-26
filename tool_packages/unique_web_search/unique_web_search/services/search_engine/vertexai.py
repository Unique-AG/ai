import asyncio
import logging
from typing import Literal

from httpx import AsyncClient
from pydantic import Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)
from unique_web_search.services.search_engine.utils.vertexai import (
    PostProcessFunction,
    add_citations,
    generate_content,
    get_vertex_client,
    get_vertex_grounding_config,
    get_vertex_structured_results_config,
    parse_to_structured_results,
)

_LOGGER = logging.getLogger(__name__)


class VertexAIConfig(BaseSearchEngineConfig[SearchEngineType.VERTEXAI]):
    search_engine_name: Literal[SearchEngineType.VERTEXAI] = SearchEngineType.VERTEXAI

    model_name: str = Field(
        default="gemini-2.5-flash",
        description="The name of the model to use for the search.",
    )
    grounding_system_instruction: str | None = Field(
        default=None,
        description="The system instruction to use for the grounding.",
    )

    requires_scraping: bool = Field(
        default=False,
        description="Whether the search engine requires scraping.",
    )
    enable_entreprise_search: bool = Field(
        default=False,
        description="Whether to use the enterprise search.",
    )

    enable_redirect_resolution: bool = Field(
        default=True,
        description="Whether to enable redirect resolution.",
    )


class VertexAI(SearchEngine[VertexAIConfig]):
    def __init__(
        self,
        config: VertexAIConfig,
        language_model_service: LanguageModelService,
        lmi: LMI,
    ):
        super().__init__(config)
        self.language_model_service = language_model_service
        self.lmi = lmi
        self.client = get_vertex_client()
        self.is_configured = self.client is not None

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        assert self.client is not None, "VertexAI client is not configured"

        # Generate the answer with citations
        answer_with_citations = await generate_content(
            client=self.client,
            model_name=self.config.model_name,
            config=get_vertex_grounding_config(
                system_instruction=self.config.grounding_system_instruction,
                entreprise_search=self.config.enable_entreprise_search,
            ),
            contents=query,
            post_process_function=PostProcessFunction[str](add_citations),
        )

        # Generate the structured results
        structured_results = await generate_content(
            client=self.client,
            model_name=self.config.model_name,
            config=get_vertex_structured_results_config(
                system_instruction=None,
                response_schema=WebSearchResults,
            ),
            contents=answer_with_citations,
            post_process_function=PostProcessFunction[WebSearchResults](
                parse_to_structured_results,
                response_schema=WebSearchResults,
            ),
        )
        if self.config.enable_redirect_resolution:
            structured_results = await resolve_all(structured_results)

        return structured_results.results


async def resolve_url(client: AsyncClient, web_search_result: WebSearchResult):
    try:
        resp = await client.head(web_search_result.url, follow_redirects=True)
        web_search_result.url = str(resp.url)
        return web_search_result
    except Exception as e:
        _LOGGER.error(f"Unable to redirect URL: {web_search_result.url}: {e}")
        return web_search_result


async def resolve_all(web_search_results: WebSearchResults):
    async with AsyncClient(follow_redirects=True, timeout=10) as client:
        tasks = [resolve_url(client, result) for result in web_search_results.results]
        results = await asyncio.gather(*tasks)
        return WebSearchResults(results=results)
