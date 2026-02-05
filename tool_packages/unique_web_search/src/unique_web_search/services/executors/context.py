"""Context classes for executor dependency injection.

This module provides container classes that group related dependencies
for web search executors, reducing parameter redundancy in __init__ methods.
"""

from dataclasses import dataclass
from typing import Optional, Protocol, TypeVar

from pydantic import BaseModel
from unique_toolkit import LanguageModelService
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ToolProgressReporter,
)

from unique_web_search.services.content_processing import ContentProcessor, WebPageChunk
from unique_web_search.services.crawlers import CrawlerTypes
from unique_web_search.services.search_engine import SearchEngineTypes
from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.utils import WebSearchDebugInfo

ElicitationModel = TypeVar("ElicitationModel", bound=BaseModel)


@dataclass
class ExecutorServiceContext:
    """Container for all service dependencies used by executors.

    Groups together all the external services that executors depend on,
    making it easier to pass dependencies and reducing parameter redundancy.

    Attributes:
        search_service: Service for performing web searches
        crawler_service: Service for crawling and extracting web page content
        content_processor: Service for processing and analyzing content
        language_model_service: Service for language model operations
        chunk_relevancy_sorter: Optional service for sorting content chunks by relevance
    """

    search_engine_service: SearchEngineTypes
    crawler_service: CrawlerTypes
    content_processor: ContentProcessor
    language_model_service: LanguageModelService
    chunk_relevancy_sorter: ChunkRelevancySorter | None


@dataclass
class ExecutorConfiguration:
    """Container for all configuration parameters used by executors.

    Groups together all configuration values and metadata that executors need,
    providing a clean separation between services and configuration.

    Attributes:
        language_model: Language model identifier and configuration
        chunk_relevancy_sort_config: Configuration for chunk relevancy sorting
        company_id: Identifier for the company/organization
        debug_info: Container for debug information and metrics
    """

    language_model: LMI
    chunk_relevancy_sort_config: ChunkRelevancySortConfig
    company_id: str
    debug_info: WebSearchDebugInfo


class ContentReducer(Protocol):
    def __call__(self, web_page_chunks: list[WebPageChunk]) -> list[WebPageChunk]: ...


class MessageLogCallback(Protocol):
    async def log_progress(self, progress_message: str) -> None: ...

    async def log_queries(self, queries: list[str]) -> None: ...

    async def log_web_search_results(
        self, web_search_results: list[WebSearchResult]
    ) -> None: ...


class QueryElicitationProtocol(Protocol):
    async def __call__(self, queries: list[str]) -> list[str]: ...


@dataclass
class ExecutorCallbacks:
    """Container for callback functions used by executors.

    Groups together all callback functions and optional reporters,
    making the callback interface clear and extensible.

    Attributes:
        message_log_callback: Callback for logging messages and progress
        content_reducer: Function to reduce content chunks based on token limits
        query_elicitation_creator: Function to create query elicitations
        query_elicitation_evaluator: Function to evaluate query elicitations
        tool_progress_reporter: Optional reporter for tool execution progress
    """

    message_log_callback: MessageLogCallback
    content_reducer: ContentReducer
    query_elicitation: QueryElicitationProtocol
    tool_progress_reporter: Optional[ToolProgressReporter] = None
