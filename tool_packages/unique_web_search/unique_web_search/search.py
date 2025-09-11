from enum import Enum
from logging import Logger
from time import time
from urllib.parse import urlparse

from pydantic import BaseModel
from tiktoken import get_encoding
from unique_toolkit import LanguageModelService
from unique_toolkit.language_model import (
    LanguageModelFunction,
)
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)

from unique_web_search.services.preprocessing.crawlers import CrawlerTypes
from unique_web_search.services.search_engine import SearchEngineTypes

class SearchMode(StrEnum):
    ADVANCED = "advanced"
    MEDIUM = "medium"
    BASIC = "simple"

async def search_web(
    tool_call: LanguageModelFunction,
    query: str,
    search_mode: SearchMode,
    search_engine: SearchEngineTypes,
    crawler: CrawlerTypes,
    tool_progress_reporter: ToolProgressReporter | None,
    language_model_service: LanguageModelService,
    logger: Logger,
) -> ToolCallResponse:
    if search_mode == SearchMode.ADVANCED:
        return await search_engine.search(query)
    elif search_mode == SearchMode.MEDIUM:
        return await search_engine.search(query)
    elif search_mode == SearchMode.BASIC:
        return await search_engine.search(query)