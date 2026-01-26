import logging
from abc import ABC, abstractmethod
from time import time

from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
)
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction

from unique_web_search.schema import WebSearchPlan, WebSearchToolParameters
from unique_web_search.services.content_processing import WebPageChunk
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
    WebSearchLogEntry,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.utils import StepDebugInfo

_LOGGER = logging.getLogger(__name__)


class BaseWebSearchExecutor(ABC):
    def __init__(
        self,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchPlan | WebSearchToolParameters,
    ):
        # Extract from service context
        self.search_service = services.search_engine_service
        self.crawler_service = services.crawler_service
        self.content_processor = services.content_processor
        self.language_model_service = services.language_model_service
        self.chunk_relevancy_sorter = services.chunk_relevancy_sorter

        # Extract from configuration
        self.language_model = config.language_model
        self.chunk_relevancy_sort_config = config.chunk_relevancy_sort_config
        self.company_id = config.company_id
        self.debug_info = config.debug_info

        # Extract from callbacks
        self._message_log_callback = callbacks.message_log_callback
        self.content_reducer = callbacks.content_reducer
        self.query_elicitation_creator = callbacks.query_elicitation_creator
        self.query_elicitation_evaluator = callbacks.query_elicitation_evaluator
        self.tool_progress_reporter = callbacks.tool_progress_reporter

        # Store tool parameters
        self.tool_call = tool_call
        self.tool_parameters = tool_parameters

        # Initialize notification state
        self._notify_name = ""
        self._notify_message = ""

        async def notify_callback() -> None:
            _LOGGER.debug(f"{self.notify_name}: {self.notify_message}")
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

    @abstractmethod
    async def run(
        self,
    ) -> tuple[list[ContentChunk], list[WebSearchLogEntry]]:
        raise NotImplementedError("Subclasses must implement this method.")

    async def _content_processing(
        self, objective: str, web_search_results: list[WebSearchResult]
    ) -> list[WebPageChunk]:
        start_time = time()
        _LOGGER.info(
            f"Company {self.company_id} Content processing with {self.content_processor.config.strategy}"
        )
        content_results = await self.content_processor.run(
            objective, web_search_results
        )
        end_time = time()
        delta_time = end_time - start_time
        _LOGGER.info(
            f"Content processed with {self.content_processor.config.strategy} completed in {delta_time} seconds"
        )
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="content_processing",
                execution_time=delta_time,
                config=self.content_processor.config.strategy.name,
                extra={
                    "number_of_results": len(web_search_results),
                    "web_page_chunks": [elem.model_dump() for elem in content_results],
                },
            )
        )
        self.debug_info.web_page_chunks = content_results
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
            _LOGGER.info(f"Sorting chunks message: {sorted_chunks.user_message}")
            return sorted_chunks.content_chunks
        else:
            return content

    async def _elicitate_queries(self, queries: list[str]) -> list[str]:
        # Create a query elicitation
        elicitation = await self.query_elicitation_creator(queries)

        _LOGGER.info(f"Query `{queries}` elicitation created: {elicitation.id}")

        # Wait for the elicitation to be accepted
        try:
            elicitation_accepted = await self.query_elicitation_evaluator(
                elicitation.id
            )
            return elicitation_accepted
        except Exception as e:
            _LOGGER.exception(f"Error eliciting queries: {e}")
            return []
