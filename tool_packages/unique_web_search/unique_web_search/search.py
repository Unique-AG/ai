import json
from enum import StrEnum
from logging import Logger
from time import time
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, create_model
from tiktoken import get_encoding
from unique_toolkit import LanguageModelService
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel
from unique_toolkit.language_model import (
    LanguageModelFunction,
    LanguageModelName,
)
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)

from unique_web_search.prompts import (
    REFINE_QUERY_SYSTEM_PROMPT,
    RESTRICT_DATE_DESCRIPTION,
)
from unique_web_search.services.agents.plan_agent import (
    PlanningMode,
    create_research_plan,
)
from unique_web_search.services.agents.plan_executor import PlanExecutor
from unique_web_search.services.crawlers import CrawlerTypes
from unique_web_search.services.search_and_crawl import SearchAndCrawlService
from unique_web_search.services.search_engine import SearchEngineTypes


class SearchMode(StrEnum):
    ADVANCED = "advanced"
    MEDIUM = "medium"
    BASIC = "simple"


def basic_search():
    # Refine the query

    # Execute the search

    # Crawl the results:

    return


def medium_search():
    # Break Down the query into subqueries

    # Execute the search

    # Identify the most relevant sources with LLM

    # Crawl the results

    return


async def advanced_search(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LanguageModelName,
    mode: PlanningMode,
    context: str | None,
    search_service: SearchEngineTypes,
    crawler_service: CrawlerTypes,
    tool_call: LanguageModelFunction,
    tool_progress_reporter: ToolProgressReporter | None,
    encoder_name: str,
    percentage_of_input_tokens_for_sources: float,
    token_limit_input: int,
):
    # Create a plan with LLM
    plan = await create_research_plan(
        query, language_model_service, language_model, mode, context
    )
    # Execute the plan

    executor = PlanExecutor(
        search_service,
        language_model_service,
        language_model,
        crawler_service,
        tool_call,
        tool_progress_reporter,
        encoder_name=encoder_name,
        percentage_of_input_tokens_for_sources=percentage_of_input_tokens_for_sources,
        token_limit_input=token_limit_input,
    )

    result = await executor.execute_plan(plan)

    return ToolCallResponse(
        id=tool_call.id,  # type: ignore
        name=tool_call.name,
        content=result.model_dump_json(),
    )
