import logging
from abc import ABC, abstractmethod
from time import time
from typing import Generic, TypeVar

from pydantic import BaseModel
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.chunk_relevancy_sorter.schemas import (
    ChunkRelevancySorterResult,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
)
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.monitoring import metric_scope

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


def _append_chunk_relevancy_invocation_stats(
    sorter_result: ChunkRelevancySorterResult,
    config: ChunkRelevancySortConfig,
    accumulator: list[LanguageModelInvocationStats],
    *,
    source: str,
    fallback_source: str,
) -> None:
    """Remap per-chunk relevancy stats onto tool-scoped source names."""
    primary_name = config.language_model.name
    fallback_name = (
        config.fallback_language_model.name
        if config.fallback_language_model is not None
        else None
    )
    for chunk_relevancy in sorter_result.relevancies:
        relevancy = chunk_relevancy.relevancy
        if relevancy is None:
            continue
        for stat in relevancy.invocation_stats:
            if stat.token_usage is None:
                continue
            # Only label fallback when the configured models differ; identical
            # names cannot distinguish primary vs fallback after the fact.
            is_fallback = (
                fallback_name is not None
                and fallback_name != primary_name
                and stat.model_name == fallback_name
            )
            accumulator.append(
                LanguageModelInvocationStats.from_usage(
                    stat.model_name,
                    stat.token_usage,
                    source=fallback_source if is_fallback else source,
                )
            )


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
                objective, web_search_results, debug_info=self.debug_info
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
            _append_chunk_relevancy_invocation_stats(
                sorted_chunks,
                self.chunk_relevancy_sort_config,
                self.debug_info.invocation_stats,
                source="web_search_chunk_relevancy",
                fallback_source="web_search_chunk_relevancy_fallback",
            )
            _LOGGER.info(f"Sorting chunks message: {sorted_chunks.user_message}")
            return sorted_chunks.content_chunks
        else:
            return content
