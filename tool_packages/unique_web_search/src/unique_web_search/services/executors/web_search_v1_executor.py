import logging
from time import time
from typing import Literal, overload, override

from pydantic import Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel
from unique_toolkit._common.validators import LMI
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.schema import WebSearchToolParameters
from unique_web_search.services.executors.base_executor import (
    BaseWebSearchExecutor,
)
from unique_web_search.services.executors.configs import RefineQueryMode
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.utils import (
    StepDebugInfo,
    query_params_to_human_string,
)

_LOGGER = logging.getLogger(__name__)


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
    mode: Literal[RefineQueryMode.DEACTIVATED],
) -> RefinedQuery: ...


@overload
async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LMI,
    system_prompt: str,
    mode: Literal[RefineQueryMode.BASIC],
) -> RefinedQuery: ...


@overload
async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LMI,
    system_prompt: str,
    mode: Literal[RefineQueryMode.ADVANCED],
) -> RefinedQueries: ...


async def query_generation_agent(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LMI,
    system_prompt: str,
    mode: RefineQueryMode,
) -> RefinedQuery | RefinedQueries:
    """Refine the query to be more specific and relevant to the user's question."""
    match mode:
        case RefineQueryMode.DEACTIVATED:
            _LOGGER.info("Query Refinement deactivated")
            ### Early return for deactivated mode
            return RefinedQuery(
                objective=query,
                refined_query=query,
            )
        case RefineQueryMode.BASIC:
            _LOGGER.info("Query Refinement with basic mode")
            structured_output_model = RefinedQuery
        case RefineQueryMode.ADVANCED:
            _LOGGER.info("Query Refinement with advanced mode")
            structured_output_model = RefinedQueries
        case _:
            raise ValueError(f"Invalid refine query mode: {mode}")

    messages = (
        MessagesBuilder()
        .system_message_append(system_prompt)
        .user_message_append(query)
        .build()
    )

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
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchToolParameters,
        refine_query_system_prompt: str,
        mode: RefineQueryMode = RefineQueryMode.BASIC,
        max_queries: int = 10,
    ):
        super().__init__(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=tool_parameters,
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

        await self._message_log_callback.log_progress(
            f"_Refining Query:_ {self.notify_message}"
        )
        refined_queries, objective = await self._refine_query(query)

        elicitated_queries = await self._ff_elicitate_queries(refined_queries)

        web_search_results = []
        # Pass query strings only - callback handles creating WebSearchLogEntry objects

        queries_wo_results = [
            query_params_to_human_string(refined_query, date_restrict)
            for refined_query in elicitated_queries
        ]
        await self._message_log_callback.log_queries(queries_wo_results)

        for index, query in enumerate(elicitated_queries):
            if len(elicitated_queries) > 1:
                self.notify_name = (
                    f"**Searching Web {index + 1}/{len(elicitated_queries)}**"
                )
            else:
                self.notify_name = "**Searching Web**"

            self.notify_message = query_params_to_human_string(query, date_restrict)
            await self.notify_callback()
            await self._message_log_callback.log_progress(self.notify_message)

            search_results = await self._search(query, date_restrict=date_restrict)

            await self._message_log_callback.log_web_search_results(search_results)

            web_search_results.extend(search_results)

        if self.search_service.requires_scraping:
            self.notify_name = "**Crawling URLs**"
            self.notify_message = f"{len(web_search_results)} URLs to fetch"
            await self.notify_callback()
            await self._message_log_callback.log_progress("_Crawling URLs_")
            crawl_results = await self._crawl(web_search_results)
            for web_search_result, crawl_result in zip(
                web_search_results, crawl_results
            ):
                web_search_result.content = crawl_result

        self.notify_name = "**Analyzing Web Pages**"
        self.notify_message = objective
        await self.notify_callback()
        await self._message_log_callback.log_progress("_Analyzing Web Pages_")

        content_results = await self._content_processing(objective, web_search_results)

        if self.chunk_relevancy_sort_config.enabled:
            self.notify_name = "**Resorting Sources**"
            self.notify_message = objective
            await self.notify_callback()
            await self._message_log_callback.log_progress("_Resorting Sources_")

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
        _LOGGER.info(f"Company {self.company_id} Searching with {self.search_service}")
        search_results = await self.search_service.search(
            query, date_restrict=date_restrict
        )
        end_time = time()
        delta_time = end_time - start_time
        _LOGGER.info(
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
        _LOGGER.info(f"Company {self.company_id} Crawling with {self.crawler_service}")
        crawl_results = await self.crawler_service.crawl(
            [result.url for result in web_search_results]
        )
        end_time = time()
        delta_time = end_time - start_time
        _LOGGER.info(
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
            _LOGGER.info(
                f"Company {self.company_id} Reducing number of queries to {self.max_queries}"
            )
            list_of_queries = list_of_queries[: self.max_queries]
        return list_of_queries
