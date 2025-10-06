import logging
from enum import StrEnum
from time import time
from typing import Callable, Literal, Optional, overload, override

from pydantic import Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ToolProgressReporter,
)
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.schema import WebSearchToolParameters
from unique_web_search.services.content_processing import ContentProcessor, WebPageChunk
from unique_web_search.services.crawlers import CrawlerTypes
from unique_web_search.services.executors.base_executor import BaseWebSearchExecutor
from unique_web_search.services.search_engine import SearchEngineTypes
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.utils import (
    StepDebugInfo,
    WebSearchDebugInfo,
    query_params_to_human_string,
)

logger = logging.getLogger(__name__)


class RefineQueryMode(StrEnum):
    ADVANCED = "advanced"
    BASIC = "basic"


class RefinedQuery(StructuredOutputModel):
    """A refined query."""

    objective: str = Field(description="The objective of the original query")
    refined_query: str = Field(
        description="The refined query optimized for the search engine."
    )


class RefinedQueries(StructuredOutputModel):
    """A refined query."""

    objective: str = Field(description="The overall objective of the original query")
    refined_queries: list[RefinedQuery] = Field(
        description="The refined queries optimized for the search engine."
    )


@overload
async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LMI,
    system_prompt: str,
    mode: Literal[RefineQueryMode.BASIC],
) -> RefinedQueries: ...


@overload
async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LMI,
    system_prompt: str,
    mode: Literal[RefineQueryMode.ADVANCED],
) -> RefinedQuery: ...


async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LMI,
    system_prompt: str,
    mode: RefineQueryMode,
) -> RefinedQuery | RefinedQueries:
    """Refine the query to be more specific and relevant to the user's question."""
    messages = (
        MessagesBuilder()
        .system_message_append(system_prompt)
        .user_message_append(query)
        .build()
    )

    if mode == RefineQueryMode.BASIC:
        structured_output_model = RefinedQueries
    else:
        structured_output_model = RefinedQuery

    response = await language_model_service.complete_async(
        messages,
        model_name=language_model.name,
        structured_output_model=structured_output_model,
        structured_output_enforce_schema=True,
    )

    parsed_response = response.choices[0].message.parsed
    if parsed_response is None:
        raise ValueError("Failed to parse insights from LLM response")

    return structured_output_model.model_validate(parsed_response)


class WebSearchV1Executor(BaseWebSearchExecutor):
    """Executes research plans step by step."""

    @override
    def __init__(
        self,
        company_id: str,
        language_model_service: LanguageModelService,
        language_model: LMI,
        search_service: SearchEngineTypes,
        crawler_service: CrawlerTypes,
        content_processor: ContentProcessor,
        chunk_relevancy_sorter: ChunkRelevancySorter | None,
        chunk_relevancy_sort_config: ChunkRelevancySortConfig,
        content_reducer: Callable[[list[WebPageChunk]], list[WebPageChunk]],
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchToolParameters,
        refine_query_system_prompt: str,
        debug_info: WebSearchDebugInfo,
        tool_progress_reporter: Optional[ToolProgressReporter] = None,
        mode: RefineQueryMode = RefineQueryMode.BASIC,
        max_queries: int = 10,
    ):
        super().__init__(
            search_service=search_service,
            language_model_service=language_model_service,
            language_model=language_model,
            crawler_service=crawler_service,
            tool_call=tool_call,
            tool_parameters=tool_parameters,
            company_id=company_id,
            content_processor=content_processor,
            chunk_relevancy_sorter=chunk_relevancy_sorter,
            chunk_relevancy_sort_config=chunk_relevancy_sort_config,
            debug_info=debug_info,
            content_reducer=content_reducer,
            tool_progress_reporter=tool_progress_reporter,
        )
        self.mode = mode
        self.tool_parameters = tool_parameters
        self.refine_query_system_prompt = refine_query_system_prompt
        self.max_queries = max_queries

    async def run(self) -> list[ContentChunk]:
        query = self.tool_parameters.query
        date_restrict = self.tool_parameters.date_restrict

        self.notify_name = "**Refining Query**"
        self.notify_message = query_params_to_human_string(query, date_restrict)
        await self.notify_callback()
        refined_queries, objective = await self._refine_query(query)

        web_search_results = []
        for index, refined_query in enumerate(refined_queries):
            if len(refined_queries) > 1:
                self.notify_name = (
                    f"**Searching Web {index + 1}/{len(refined_queries)}**"
                )
            else:
                self.notify_name = "**Searching Web**"

            self.notify_message = query_params_to_human_string(
                refined_query, date_restrict
            )
            await self.notify_callback()

            search_results = await self._search(
                refined_query, date_restrict=date_restrict
            )
            web_search_results.extend(search_results)

        if self.search_service.requires_scraping:
            self.notify_name = "**Crawling URLs**"
            self.notify_message = f"{len(web_search_results)} URLs to fetch"
            await self.notify_callback()
            crawl_results = await self._crawl(web_search_results)
            for web_search_result, crawl_result in zip(
                web_search_results, crawl_results
            ):
                web_search_result.content = crawl_result

        self.notify_name = "**Analyzing Web Pages**"
        self.notify_message = objective
        await self.notify_callback()

        content_results = await self._content_processing(objective, web_search_results)

        if self.chunk_relevancy_sorter:
            self.notify_name = "**Resorting Sources**"
            self.notify_message = objective
            await self.notify_callback()

        relevant_sources = await self._select_relevant_sources(
            objective, content_results
        )

        return relevant_sources

    async def _refine_query(self, query: str) -> tuple[list[str], str]:
        start_time = time()
        refined_query = await query_generation_agent(
            query,
            self.language_model_service,
            self.language_model,
            self.refine_query_system_prompt,
            self.mode,
        )
        end_time = time()
        delta_time = end_time - start_time

        if isinstance(refined_query, RefinedQuery):
            queries = [refined_query.refined_query]
        elif isinstance(refined_query, RefinedQueries):
            queries = [
                refined_query.refined_query
                for refined_query in refined_query.refined_queries
            ]
        else:
            raise ValueError("Invalid refined query")
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="refine_query",
                execution_time=delta_time,
                config=self.mode.name,
                extra={
                    "query": query,
                    "refined_queries": queries,
                },
            )
        )

        return queries, refined_query.objective

    async def _search(
        self, query: str, date_restrict: str | None
    ) -> list[WebSearchResult]:
        start_time = time()
        logger.info(f"Company {self.company_id} Searching with {self.search_service}")
        search_results = await self.search_service.search(
            query, date_restrict=date_restrict
        )
        end_time = time()
        delta_time = end_time - start_time
        logger.info(
            f"Searched with {self.search_service} completed in {delta_time} seconds"
        )
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="search",
                execution_time=delta_time,
                config=self.search_service.config.search_engine_name.name,
                extra={
                    "query": query,
                    "date_restrict": date_restrict,
                    "number_of_results": len(search_results),
                    "urls": [result.url for result in search_results],
                },
            )
        )
        return search_results

    async def _crawl(self, web_search_results: list[WebSearchResult]) -> list[str]:
        start_time = time()
        logger.info(f"Company {self.company_id} Crawling with {self.crawler_service}")
        crawl_results = await self.crawler_service.crawl(
            [result.url for result in web_search_results]
        )
        end_time = time()
        delta_time = end_time - start_time
        logger.info(
            f"Crawled {len(web_search_results)} pages with {self.crawler_service} completed in {delta_time} seconds"
        )
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="crawl",
                execution_time=delta_time,
                config=self.crawler_service.config.crawler_type.name,
                extra={
                    "number_of_results": len(web_search_results),
                    "contents": [result.model_dump() for result in web_search_results],
                },
            )
        )
        return crawl_results

    def _enforce_max_queries(self, list_of_queries: list[str]) -> list[str]:
        if len(list_of_queries) > self.max_queries:
            logger.info(
                f"Company {self.company_id} Reducing number of queries to {self.max_queries}"
            )
            list_of_queries = list_of_queries[: self.max_queries]
        return list_of_queries
