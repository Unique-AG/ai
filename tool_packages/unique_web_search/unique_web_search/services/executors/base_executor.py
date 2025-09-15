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
    ProgressState,
    ToolProgressReporter,
)

from unique_web_search.schema import WebSearchPlan, WebSearchToolParameters
from unique_web_search.services.content_processing import ContentProcessor, WebPageChunk
from unique_web_search.services.crawlers import CrawlerTypes
from unique_web_search.services.search_engine import SearchEngineTypes, WebSearchResult

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")


class BaseWebSearchExecutor:
    def __init__(
        self,
        search_service: SearchEngineTypes,
        language_model_service: LanguageModelService,
        language_model: LMI,
        crawler_service: CrawlerTypes,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchPlan | WebSearchToolParameters,
        company_id: str,
        content_processor: ContentProcessor,
        chunk_relevancy_sorter: ChunkRelevancySorter | None,
        chunk_relevancy_sort_config: ChunkRelevancySortConfig,
        content_reducer: Callable[[list[WebPageChunk]], list[WebPageChunk]],
        tool_progress_reporter: Optional[ToolProgressReporter] = None,
        debug: bool = False,
    ):
        self.company_id = company_id
        self.search_service = search_service
        self.crawler_service = crawler_service
        self.language_model_service = language_model_service
        self.tool_progress_reporter = tool_progress_reporter
        self.language_model = language_model
        self.content_processor = content_processor
        self.chunk_relevancy_sorter = chunk_relevancy_sorter
        self.chunk_relevancy_sort_config = chunk_relevancy_sort_config
        self.tool_call = tool_call
        self.tool_parameters = tool_parameters
        self.debug = debug
        self.content_reducer = content_reducer
        self._notify_name = ""
        self._notify_message = ""

        self.debug_info = {"step_info": []}

        async def notify_callback() -> None:
            logger.info(f"{self.notify_name}: {self.notify_message}")
            if self.tool_progress_reporter:
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=self.notify_name,
                    message=self.notify_message,
                    state=ProgressState.RUNNING,
                )

        self.notify_callback = notify_callback

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
        raise NotImplementedError("Subclasses must implement this method.")

    async def _content_processing(
        self, objective: str, web_search_results: list[WebSearchResult]
    ) -> list[WebPageChunk]:
        start_time = time()
        logger.info(
            f"Company {self.company_id} Content processing with {self.content_processor.config.strategy}"
        )
        content_results = await self.content_processor.run(
            objective, web_search_results
        )
        end_time = time()
        delta_time = end_time - start_time
        logger.info(
            f"Content processed with {self.content_processor.config.strategy} completed in {delta_time} seconds"
        )
        self.debug_info["step_info"].append(
            {
                "operation": "content_processing",
                "execution_time": delta_time,
                "content_processor": self.content_processor.config.strategy,
                "number_of_results": len(web_search_results),
                **(
                    {
                        "urls": [result.url for result in web_search_results],
                        "content": [elem.model_dump() for elem in content_results],
                    }
                    if self.debug
                    else {}
                ),
            }
        )
        return content_results

    async def _select_relevant_sources(
        self,
        objective: str,
        web_page_chunks: list[WebPageChunk],
    ) -> list[ContentChunk]:
        # Reduce the sources to the token limit defined in the config
        top_results = self.content_reducer(web_page_chunks)

        # Convert WebPageChunks to ContentChunk format
        content = [chunk.to_content_chunk() for chunk in top_results]

        # Apply chunk relevancy sorting
        if self.chunk_relevancy_sorter:
            sorted_chunks = await self.chunk_relevancy_sorter.run(
                input_text=objective,
                chunks=content,
                config=self.chunk_relevancy_sort_config,
            )
            logger.info(f"Sorting chunks message: {sorted_chunks.user_message}")
            return sorted_chunks.content_chunks
        else:
            return content
