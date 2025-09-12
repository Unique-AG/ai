from enum import Enum
from logging import Logger
from time import time
from urllib.parse import urlparse

from pydantic import BaseModel
from tiktoken import get_encoding
from unique_toolkit.language_model import (
    LanguageModelFunction,
)
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)

from unique_web_search.services.crawlers import CrawlerTypes


class Step(BaseModel):
    message: str
    error_message: str


class ExecutionSteps(Enum):
    SELECT_URL = Step(
        message="Selecting the URL", error_message="Failed to select the url"
    )
    CRAWL_URL = Step(
        message="Reading content from URL", error_message="Failed to crawl the url"
    )
    ANALYZE_CONTENT = Step(
        message="Analyzing the content", error_message="Failed to analyze the content"
    )


async def web_read_url(
    tool_call: LanguageModelFunction,
    urls: list[str],
    crawler: CrawlerTypes,
    tool_progress_reporter: ToolProgressReporter | None,
    encoder_name: str,
    percentage_of_input_tokens_for_sources: float,
    token_limit_input: int,
    logger: Logger,
) -> list[str]:
    """Run search and generate answer to the user query"""

    logger.info("Running the WebSearch tool")
    name = "**Web Read Url**"
    step = ExecutionSteps.SELECT_URL

    debug_info = {
        "crawler": crawler.__class__.__name__,
    }

    domains = ", ".join([f"[{urlparse(url).netloc}]({url})" for url in urls])
    
    name = f"**Web Read Url**: {domains}"


    crawl_start_time = time()
    markdown_contents = await _crawl_url(
        tool_call=tool_call,
        name=name,
        message=step.value.message,
        urls=urls,
        tool_progress_reporter=tool_progress_reporter,
        crawler=crawler,
    )
    debug_info = debug_info | {
        "crawl_time": time() - crawl_start_time,
        "markdown_content": markdown_contents,
    }

    return markdown_contents
        


async def _crawl_url(
    tool_call: LanguageModelFunction,
    name: str,
    message: str,
    urls: list[str],
    tool_progress_reporter: ToolProgressReporter | None,
    crawler: CrawlerTypes,
) -> list[str]:
    # Step 2: Crawl the URL
    if tool_progress_reporter:
        await tool_progress_reporter.notify_from_tool_call(
            name=name,
            message=message,
            tool_call=tool_call,
            state=ProgressState.RUNNING,
        )
    contents = await crawler.crawl(urls)  # type: ignore

    if not contents:
        raise ValueError("No Markdown has been retrieved from the URLs")

    return contents


async def _limit_to_token_limit(
    tool_call: LanguageModelFunction,
    name: str,
    message: str,
    markdown_content: str,
    encoder_name: str,
    percentage_of_input_tokens_for_sources: float,
    token_limit_input: int,
    tool_progress_reporter: ToolProgressReporter | None,
) -> str:
    if tool_progress_reporter:
        await tool_progress_reporter.notify_from_tool_call(
            name=name,
            message=message,
            tool_call=tool_call,
            state=ProgressState.RUNNING,
        )
    encoder = get_encoding(encoder_name)
    token_limit = percentage_of_input_tokens_for_sources * token_limit_input
    tokens = encoder.encode(markdown_content)
    if len(tokens) > token_limit:
        markdown_content = encoder.decode(tokens[:token_limit])

    return markdown_content
