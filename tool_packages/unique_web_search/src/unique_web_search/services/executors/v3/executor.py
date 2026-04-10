"""Web Search V3 executor: globally judge snippets before crawling."""

import asyncio
import logging
from time import time

from unique_toolkit.content import ContentChunk
from unique_toolkit.content.schemas import ContentMetadata
from unique_toolkit.language_model import LanguageModelFunction

from unique_web_search.schema import Step, StepDebugInfo, StepType, WebSearchPlan
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.v2.executor import (
    WebSearchV2Executor,
)
from unique_web_search.services.helpers import extract_registered_domain
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.snippet_judge import (
    SnippetJudgeConfig,
    select_relevant,
)

_LOGGER = logging.getLogger(__name__)
_WEB_SEARCH_V3_SOURCE_LABEL_KEY = "websearch_v3_source_label"


class WebSearchV3Executor(WebSearchV2Executor):
    """Executes research plans with snippet-based relevance filtering before crawling.

    V3 first collects all snippets from all search steps, then runs a single
    global snippet-judge pass across the combined result set, and only then
    crawls the top-ranked URLs. This lets the judge compare snippets across
    search queries and reward diversity globally instead of per query.
    """

    def __init__(
        self,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchPlan,
        max_steps: int = 3,
        snippet_judge_config: SnippetJudgeConfig | None = None,
    ):
        super().__init__(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=tool_parameters,
            max_steps=max_steps,
        )
        self.snippet_judge_config = snippet_judge_config or SnippetJudgeConfig()
        _LOGGER.info(
            f"Snippet judge config: {self.snippet_judge_config.model_dump_json()}"
        )

    async def run(self) -> list[ContentChunk]:
        await self._enforce_max_steps()

        self.notify_name = "**Searching Web**"
        self.notify_message = self.tool_parameters.objective

        await self.notify_callback()
        await self._message_log_callback.log_progress("_Searching Web_")

        elicited_steps = await self._elicitate_steps(self.tool_parameters.steps)
        search_steps = [
            step for step in elicited_steps if step.step_type == StepType.SEARCH
        ]
        read_url_steps = [
            step for step in elicited_steps if step.step_type == StepType.READ_URL
        ]

        search_results_nested, read_url_results_nested = await asyncio.gather(
            self._run_search_steps(search_steps),
            self._run_read_url_steps(read_url_steps),
        )

        search_results = self._flatten_results(search_results_nested)
        read_url_results = self._flatten_results(read_url_results_nested)

        if self.search_service.requires_scraping and search_results:
            search_results = await self._judge_all_search_results(search_results)
            if search_results:
                search_results = await self._crawl_search_results(
                    "SEARCH.global", search_results
                )

        results = search_results + read_url_results

        self.notify_name = "**Analyzing Web Pages**"
        self.notify_message = self.tool_parameters.expected_outcome
        await self.notify_callback()
        await self._message_log_callback.log_progress("_Analyzing Web Pages_")

        content_results = await self._content_processing(
            self.tool_parameters.objective, results
        )

        if self.chunk_relevancy_sort_config.enabled:
            self.notify_name = "**Resorting Sources**"
            self.notify_message = self.tool_parameters.objective
            await self.notify_callback()
            await self._message_log_callback.log_progress("_Resorting Sources_")

        selected_chunks = await self._select_relevant_sources(
            self.tool_parameters.objective, content_results
        )
        return self._annotate_chunks_for_agent(selected_chunks)

    def _annotate_chunks_for_agent(
        self, chunks: list[ContentChunk]
    ) -> list[ContentChunk]:
        """Attach source labels only for V3 web-search chunks."""
        for chunk in chunks:
            if not chunk.url or not chunk.title:
                continue
            chunk.metadata = ContentMetadata(
                key=_WEB_SEARCH_V3_SOURCE_LABEL_KEY,
                mime_type="text/plain",
                document=chunk.title,
            )
        return chunks

    async def _run_search_steps(
        self, steps: list[Step]
    ) -> list[list[WebSearchResult] | BaseException]:
        tasks = [asyncio.create_task(self._execute_search_step(step)) for step in steps]
        if not tasks:
            return []
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_read_url_steps(
        self, steps: list[Step]
    ) -> list[list[WebSearchResult] | BaseException]:
        tasks = [
            asyncio.create_task(self._execute_read_url_step(step)) for step in steps
        ]
        if not tasks:
            return []
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _flatten_results(
        self, results_nested: list[list[WebSearchResult] | BaseException]
    ) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        for result in results_nested:
            if isinstance(result, BaseException):
                _LOGGER.exception(f"Error executing step: {result}")
            else:
                results.extend(result)
        return results

    async def _execute_search_step(self, step: Step) -> list[WebSearchResult]:
        """Run the search step but defer judging/crawling until all snippets are collected."""
        step_name = step.step_type.name
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name=step_name,
                execution_time=0,
                config=step.model_dump(),
            )
        )

        time_start = time()
        _LOGGER.info(f"Company {self.company_id} Searching with {self.search_service}")

        await self._message_log_callback.log_queries([step.query_or_url])
        results = await self.search_service.search(step.query_or_url)
        await self._message_log_callback.log_web_search_results(results)

        delta_time = time() - time_start

        self.debug_info.steps.append(
            StepDebugInfo(
                step_name=f"{step_name}.search",
                execution_time=delta_time,
                config=self.search_service.config.search_engine_name.name,
                extra={
                    "query": step.query_or_url,
                    "number_of_results": len(results),
                    "urls": [result.url for result in results],
                },
            )
        )

        _LOGGER.info(
            f"Searched with {self.search_service} completed in {delta_time} seconds"
        )
        return results

    async def _judge_all_search_results(
        self,
        results: list[WebSearchResult],
    ) -> list[WebSearchResult]:
        """Run one global snippet judge pass across all collected search results."""
        if not results or not self.search_service.requires_scraping:
            return results

        number_before_judge = len(results)
        time_judge_start = time()
        _LOGGER.info(
            f"Company {self.company_id} Running global snippet judge to narrow results"
        )
        try:
            selected = await select_relevant(
                objective=self.tool_parameters.objective,
                results=results,
                language_model_service=self.language_model_service,
                language_model=self.language_model,
                config=self.snippet_judge_config,
            )
            _LOGGER.info(
                f"Company {self.company_id} Snippet judge selected {len(selected)} results from {number_before_judge}"
            )

            results = selected
        except Exception as e:
            _LOGGER.warning("Snippet judge failed, using all search results: %s", e)
            results = results[: self.snippet_judge_config.max_urls_to_select]

        judge_time = time() - time_judge_start
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="SEARCH.global.snippet_judge",
                execution_time=judge_time,
                config="snippet_judge",
                extra={
                    "number_of_results_before": number_before_judge,
                    "number_of_results_after": len(results),
                    "selected_domains": [result.display_link for result in results],
                    "selected_registered_domains": [
                        extract_registered_domain(result.url) for result in results
                    ],
                    "selected_urls": [result.url for result in results],
                },
            )
        )
        return results
