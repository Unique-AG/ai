import asyncio
import logging
from time import time

from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction

from unique_web_search.schema import (
    Step,
    StepType,
    WebSearchPlan,
)
from unique_web_search.services.executors.base_executor import (
    BaseWebSearchExecutor,
    WebSearchLogEntry,
)
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.utils import StepDebugInfo

_LOGGER = logging.getLogger(__name__)

step_type_to_name = {
    StepType.SEARCH: "**Searching Web**",
    StepType.READ_URL: "**Reading URL**",
}


class WebSearchV2Executor(BaseWebSearchExecutor):
    """Executes research plans step by step."""

    def __init__(
        self,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchPlan,
        max_steps: int = 3,
    ):
        super().__init__(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=tool_parameters,
        )

        self.tool_parameters = tool_parameters
        self.max_steps = max_steps
        self.queries_for_log: list[WebSearchLogEntry] = []

    @property
    def notify_name(self):
        return self._notify_name

    @notify_name.setter
    def notify_name(self, value):
        self._notify_name = value

    @property
    def notify_message(self):
        return self._notify_message

    @notify_message.setter
    def notify_message(self, value):
        self._notify_message = value

    async def run(self) -> tuple[list[ContentChunk], list[WebSearchLogEntry]]:
        await self._enforce_max_steps()

        results: list[WebSearchResult] = []
        self.notify_name = "**Searching Web**"
        self.notify_message = self.tool_parameters.objective
        await self.notify_callback()
        self._message_log_callback(
            progress_message="_Searching Web_", queries_for_log=self.queries_for_log
        )

        tasks = [
            asyncio.create_task(self._execute_step(step))
            for step in self.tool_parameters.steps
        ]

        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results_nested:
            if isinstance(result, BaseException):
                _LOGGER.exception(f"Error executing step: {result}")
            else:
                results.extend(result)

        # for step in self.tool_parameters.steps:
        #     self.notify_name = step_type_to_name[step.step_type]
        #     self.notify_message = step.objective
        #     await self.notify_callback()
        #     step_results = await self._execute_step(step)
        #     results.extend(step_results)

        self.notify_name = "**Analyzing Web Pages**"
        self.notify_message = self.tool_parameters.expected_outcome
        await self.notify_callback()
        self._message_log_callback(
            progress_message="_Analyzing Web Pages_",
            queries_for_log=self.queries_for_log,
        )

        content_results = await self._content_processing(
            self.tool_parameters.objective, results
        )

        if self.chunk_relevancy_sort_config.enabled:
            self.notify_name = "**Resorting Sources**"
            self.notify_message = self.tool_parameters.objective
            await self.notify_callback()
            self._message_log_callback(
                progress_message="_Resorting Sources_",
                queries_for_log=self.queries_for_log,
            )

        relevant_sources = await self._select_relevant_sources(
            self.tool_parameters.objective, content_results
        )

        return relevant_sources, self.queries_for_log

    async def _execute_step(self, step: Step) -> list[WebSearchResult]:
        if step.step_type == StepType.SEARCH:
            return await self._execute_search_step(step)
        elif step.step_type == StepType.READ_URL:
            return await self._execute_read_url_step(step)
        else:
            raise ValueError(f"Invalid step type: {type(step)}")

    async def _execute_search_step(self, step: Step) -> list[WebSearchResult]:
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

        results = await self._search_with_elicitation(step.query_or_url)
        self.queries_for_log.append(
            WebSearchLogEntry(
                type=StepType.SEARCH,
                message=step.query_or_url,
                web_search_results=results,
            )
        )

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

        if self.search_service.requires_scraping:
            time_start = time()
            _LOGGER.info(
                f"Company {self.company_id} Crawling with {self.crawler_service}"
            )
            crawl_results = await self.crawler_service.crawl(
                [result.url for result in results]
            )
            delta_time = time() - time_start
            for result, content in zip(results, crawl_results):
                result.content = content

            self.debug_info.steps.append(
                StepDebugInfo(
                    step_name=f"{step_name}.crawl",
                    execution_time=delta_time,
                    config=self.crawler_service.config.crawler_type.name,
                    extra={
                        "number_of_results": len(results),
                        "contents": [result.model_dump() for result in results],
                    },
                )
            )
            _LOGGER.info(
                f"Crawled {len(results)} pages with {self.crawler_service} completed in {delta_time} seconds"
            )
        return results

    async def _execute_read_url_step(self, step: Step) -> list[WebSearchResult]:
        step_name = step.step_type.name
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name=step_name,
                execution_time=0,
                config=step.model_dump(),
            )
        )
        time_start = time()
        _LOGGER.info(f"Company {self.company_id} Crawling with {self.crawler_service}")
        results = await self.crawler_service.crawl([step.query_or_url])
        self.queries_for_log.append(
            WebSearchLogEntry(
                type=StepType.READ_URL,
                message=f"{step.query_or_url}",
                web_search_results=[
                    WebSearchResult(
                        url=step.query_or_url,
                        content=results[0],  # .content or "",
                        snippet=step.objective,
                        title=step.objective,
                    )
                ],
            )
        )
        delta_time = time() - time_start
        _LOGGER.debug(
            f"Crawled {step.query_or_url} with {self.crawler_service} completed in {delta_time} seconds"
        )

        self.debug_info.steps.append(
            StepDebugInfo(
                step_name=f"{step_name}.crawl",
                execution_time=delta_time,
                config=self.crawler_service.config.crawler_type.name,
                extra={
                    "url": step.query_or_url,
                    "content": results,
                },
            )
        )
        results = [
            WebSearchResult(url=step.query_or_url, content=result, snippet="", title="")
            for result in results
        ]
        return results

    async def _enforce_max_steps(self) -> None:
        if len(self.tool_parameters.steps) > self.max_steps:
            _LOGGER.warning(
                f"Number of steps is greater than the maximum number of steps: {len(self.tool_parameters.steps)} > {self.max_steps}"
            )
            _LOGGER.info(f"Reducing number of steps to {self.max_steps}")
            self.tool_parameters.steps = self.tool_parameters.steps[: self.max_steps-1]
            self.debug_info.steps.append(
                StepDebugInfo(
                    step_name="enforce_max_steps",
                    execution_time=0,
                    config=self.tool_parameters.model_dump(),
                    extra={
                        "max_steps": self.max_steps,
                        "number_of_planned_steps": len(self.tool_parameters.steps),
                    },
                )
            )
