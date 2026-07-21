import logging
from abc import ABC, abstractmethod
from time import time
from typing import Generic, TypeVar

from pydantic import BaseModel
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
)
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction
from unique_toolkit.monitoring import metric_scope

from unique_web_search.invocation_stats import record_invocation_stats
from unique_web_search.metrics import llm_duration, llm_errors
from unique_web_search.schema import (
    StepDebugInfo,
    WebPageChunk,
)
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

_LOGGER = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)


class BaseWebSearchExecutor(ABC, Generic[T]):
    def __init__(
        self,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        tool_parameters: T,
        exposed_params_cls: type[ExposedParams] | None = None,
    ):
        # Extract from service context
        self.search_service = services.search_engine_service
        self.crawler_service = services.crawler_service
        self.content_processor = services.content_processor
        self.language_model_service = services.language_model_service
        self.chunk_relevancy_sorter = services.chunk_relevancy_sorter

        # Extract from configuration
        self.chunk_relevancy_sort_config = config.chunk_relevancy_sort_config
        self.company_id = config.company_id
        self.debug_info = config.debug_info

        # Extract from callbacks
        self._message_log_callback = callbacks.message_log_callback
        self.content_reducer = callbacks.content_reducer
        self.query_elicitation = callbacks.query_elicitation
        self.tool_progress_reporter = callbacks.tool_progress_reporter

        # Store tool parameters
        self.tool_call = tool_call
        self.tool_parameters = tool_parameters
        self.exposed_params_cls = exposed_params_cls

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

    def _extract_search_params(self, source: BaseModel) -> ExposedParams | None:
        """Validate ``source`` against the exposed-params class, dropping tool-only fields.

        Returns ``None`` when no knobs are exposed for this deployment. Otherwise
        re-validates the source dump through ``exposed_params_cls``
        (``extra="ignore"``) so only admin-exposed engine knobs remain.
        """
        if self.exposed_params_cls is None:
            return None
        return self.exposed_params_cls.model_validate(source.model_dump(by_alias=True))

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
    async def run(self) -> list[ContentChunk]:
        raise NotImplementedError("Subclasses must implement this method.")

    async def _content_processing(
        self, objective: str, web_search_results: list[WebSearchResult]
    ) -> list[WebPageChunk]:
        start_time = time()
        _LOGGER.info(
            f"Company {self.company_id} Content processing with {self.content_processor.config.active_processing_strategies}"
        )
        with metric_scope(llm_duration, llm_errors, purpose="content_processing"):
            content_results = await self.content_processor.run(
                objective, web_search_results
            )
        end_time = time()
        delta_time = end_time - start_time
        _LOGGER.info(
            f"Content processed with {self.content_processor.config.active_processing_strategies} completed in {delta_time} seconds"
        )
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="content_processing",
                execution_time=delta_time,
                config=str(self.content_processor.config.active_processing_strategies),
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
            # The relevancy sorter makes one LLM call per chunk and attaches the
            # usage to each ChunkRelevancy.relevancy.invocation_stats; merge it
            # into the active WebSearch stats scope so it isn't dropped from
            # token analytics (Internal Search does the same after its sort).
            record_invocation_stats(
                invocation
                for relevancy in sorted_chunks.relevancies
                if relevancy.relevancy is not None
                for invocation in relevancy.relevancy.invocation_stats
            )
            _LOGGER.info(f"Sorting chunks message: {sorted_chunks.user_message}")
            return sorted_chunks.content_chunks
        else:
            return content
