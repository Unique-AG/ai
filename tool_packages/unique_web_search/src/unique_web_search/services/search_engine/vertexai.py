import asyncio
import logging
from typing import Annotated, Literal

from httpx import AsyncClient as HttpxAsyncClient
from httpx import HTTPError
from pydantic import Field
from unique_toolkit._common.default_language_model import DEFAULT_LANGUAGE_MODEL
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.language_model import LanguageModelService

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
    get_search_engine_model_config,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)
from unique_web_search.services.search_engine.utils.grounding import (
    GENERATION_INSTRUCTIONS,
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


class VertexAIConfig(BaseSearchEngineConfig[SearchEngineType.VERTEXAI]):
    model_config = get_search_engine_model_config(SearchEngineType.VERTEXAI)
    search_engine_name: Literal[SearchEngineType.VERTEXAI] = SearchEngineType.VERTEXAI

    vertexai_model_name: str = Field(
        default="gemini-3-flash-preview",
        description="The name of the model to use for the search.",
    )

    generation_instructions: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(GENERATION_INSTRUCTIONS.split("\n"))
        ),
    ] = Field(
        default=GENERATION_INSTRUCTIONS,
        description="The generation instructions to be injected into the Microsoft Foundry Agents.",
    )

    fallback_language_model: LMI = get_LMI_default_field(
        DEFAULT_LANGUAGE_MODEL,
        description="The language model to use as a fallback parser if the grounding response is not valid JSON.",
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
    ):
        super().__init__(config=config)
        self._client = get_vertex_client()
        self.is_configured = self._client is not None

        self.response_parsers = [
            JsonConversionStrategy(),
            LLMParserStrategy(
                config.fallback_language_model,
                language_model_service,
            ),
        ]

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        assert self._client is not None, "VertexAI client is not configured"

        response = await generate_vertexai_response(
            client=self._client,
            model_name=self.config.vertexai_model_name,
            config=get_vertex_grounding_with_structured_output_config(
                generation_instructions=self.config.generation_instructions,
                entreprise_search=self.config.enable_entreprise_search,
            ),
            contents=query,
        )

        answer_with_citations = add_citations(response)

        results = await convert_response_to_search_results(
            answer_with_citations, self.response_parsers
        )

        if self.config.enable_redirect_resolution:
            resolved = await resolve_all(WebSearchResults(results=results))
            results = resolved.results

        return results


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
