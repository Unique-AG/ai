import logging
from time import time
from typing import Callable, Optional

from unique_toolkit import LanguageModelService
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit._common.validators import LMI
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction
from unique_toolkit.tools.tool_progress_reporter import (
    ToolProgressReporter,
)

from unique_web_search.schema import STEP_TYPES, ReadUrlStep, SearchStep, WebSearchPlan
from unique_web_search.services.content_processing import ContentProcessor, WebPageChunk
from unique_web_search.services.crawlers import CrawlerTypes
from unique_web_search.services.executors.base_executor import BaseWebSearchExecutor
from unique_web_search.services.search_engine import SearchEngineTypes, WebSearchResult

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")

step_type_to_name = {
    SearchStep.step_type: "**Searching Web**",
    ReadUrlStep.step_type: "**Reading URL**",
}


class WebSearchV2Executor(BaseWebSearchExecutor):
    """Executes research plans step by step."""

    def __init__(
        self,
        search_service: SearchEngineTypes,
        language_model_service: LanguageModelService,
        language_model: LMI,
        crawler_service: CrawlerTypes,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchPlan,
        company_id: str,
        content_processor: ContentProcessor,
        chunk_relevancy_sorter: ChunkRelevancySorter | None,
        chunk_relevancy_sort_config: ChunkRelevancySortConfig,
        content_reducer: Callable[[list[WebPageChunk]], list[WebPageChunk]],
        tool_progress_reporter: Optional[ToolProgressReporter] = None,
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
            content_reducer=content_reducer,
            tool_progress_reporter=tool_progress_reporter,
        )

        self.tool_parameters = tool_parameters

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

    async def run(self) -> tuple[list[ContentChunk], dict]:
        results = []
        for step in self.tool_parameters.steps:
            self.notify_name = step_type_to_name[step.step_type]
            self.notify_message = step.objective
            await self.notify_callback()
            step_results = await self._execute_step(step)
            results.append(step_results)

        self.notify_name = "**Analyzing Web Pages**"
        self.notify_message = self.tool_parameters.objective
        await self.notify_callback()

        content_results = await self._content_processing(
            self.tool_parameters.objective, results
        )

        if self.chunk_relevancy_sorter:
            self.notify_name = "**Resorting Sources**"
            self.notify_message = self.tool_parameters.objective
            await self.notify_callback()

        relevant_sources = await self._select_relevant_sources(
            self.tool_parameters.objective, content_results
        )

        return relevant_sources, self.debug_info

    async def _execute_step(
        self, step: STEP_TYPES
    ) -> tuple[list[WebSearchResult], dict]:
        if isinstance(step, SearchStep):
            return await self._execute_search_step(step)
        elif isinstance(step, ReadUrlStep):
            return await self._execute_read_url_step(step)
        else:
            raise ValueError(f"Invalid step type: {type(step)}")

    async def _execute_search_step(
        self, step: SearchStep
    ) -> tuple[list[WebSearchResult], dict]:
        search_debug_info = step.model_dump()

        time_info = {}
        time_start = time()
        logger.info(
            f"Company {self.company_id} Searching with {self.search_service.__name__}"
        )

        results = await self.search_service.search(step.query)
        delta_time = time() - time_start

        time_info["search_time"] = {
            "execution_time": delta_time,
            "search_service": self.search_service.__name__,
        }
        logger.info(
            f"Searched with {self.search_service.__name__} completed in {delta_time} seconds"
        )

        if self.search_service.requires_scraping:
            time_start = time()
            logger.info(
                f"Company {self.company_id} Crawling with {self.crawler_service.__name__}"
            )
            crawl_results = await self.crawler_service.crawl(
                [result.url for result in results]
            )
            delta_time = time() - time_start
            for result, content in zip(results, crawl_results):
                result.content = content

            time_info["crawl_time"] = {
                "execution_time": delta_time,
                "crawler_service": self.crawler_service.__name__,
                "number_of_results": len(results),
                "urls": [result.url for result in results],
                "content": crawl_results,
            }
            logger.info(
                f"Crawled {len(results)} pages with {self.crawler_service.__name__} completed in {delta_time} seconds"
            )

        search_debug_info = search_debug_info | time_info

        return results, search_debug_info

    async def _execute_read_url_step(
        self, step: ReadUrlStep
    ) -> tuple[list[WebSearchResult], dict]:
        read_url_debug_info = step.model_dump()
        time_start = time()
        logger.info(
            f"Company {self.company_id} Crawling with {self.crawler_service.__name__}"
        )
        results = await self.crawler_service.crawl([step.url])
        delta_time = time() - time_start
        logger.info(
            f"Crawled {step.url} with {self.crawler_service.__name__} completed in {delta_time} seconds"
        )

        read_url_debug_info["crawl_time"] = {
            "execution_time": time() - time_start,
            "crawler_service": self.crawler_service.__name__,
            "url": step.url,
            "content": results,
        }
        results = [
            WebSearchResult(url=step.url, content=result, snippet="", title="")
            for result in results
        ]
        return results, read_url_debug_info
