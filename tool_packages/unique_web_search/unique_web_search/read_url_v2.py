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
    url: str,
    crawler: CrawlerTypes,
    tool_progress_reporter: ToolProgressReporter | None,
    encoder_name: str,
    percentage_of_input_tokens_for_sources: float,
    token_limit_input: int,
    logger: Logger,
) -> ToolCallResponse:
    """Run search and generate answer to the user query"""

    logger.info("Running the WebSearch tool")
    name = "**Web Read Url**"
    step = ExecutionSteps.SELECT_URL

    debug_info = {
        "crawler": crawler.__class__.__name__,
    }

    try:
        if tool_progress_reporter:
            await tool_progress_reporter.notify_from_tool_call(
                name=name,
                message=step.value.message,
                tool_call=tool_call,
                state=ProgressState.RUNNING,
            )

        debug_info["url"] = url
        url_domain = urlparse(url).netloc
        name = f"**Web Read Url**: {url_domain}"
        # Step 1: Crawl the URL
        step = ExecutionSteps.CRAWL_URL

        crawl_start_time = time()
        markdown_content = await _crawl_url(
            tool_call=tool_call,
            name=name,
            message=step.value.message,
            url=url,
            tool_progress_reporter=tool_progress_reporter,
            crawler=crawler,
        )
        debug_info = debug_info | {
            "crawl_time": time() - crawl_start_time,
            "markdown_content": markdown_content,
        }

        # step 2: Analyze the content
        step = ExecutionSteps.ANALYZE_CONTENT
        markdown_content = await _limit_to_token_limit(
            tool_call=tool_call,
            name=name,
            message=step.value.message,
            markdown_content=markdown_content,
            encoder_name=encoder_name,
            percentage_of_input_tokens_for_sources=percentage_of_input_tokens_for_sources,
            token_limit_input=token_limit_input,
            tool_progress_reporter=tool_progress_reporter,
        )

        # Step 4: Return Results
        if tool_progress_reporter:
            await tool_progress_reporter.notify_from_tool_call(
                name=name,
                message=step.value.message,
                tool_call=tool_call,
                state=ProgressState.FINISHED,
            )
        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=tool_call.name,
            content=markdown_content,
            debug_info=debug_info,
        )
    except Exception as e:
        if tool_progress_reporter:
            await tool_progress_reporter.notify_from_tool_call(
                name=name,
                message=step.value.message,
                tool_call=tool_call,
                state=ProgressState.FAILED,
            )
        debug_info = debug_info | {
            "error_message": step.value.error_message,
        }
        logger.exception(f"An error occurred while reading the URL: {e}")
        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=tool_call.name,
            error_message=step.value.error_message,
            debug_info=debug_info,
        )


async def _crawl_url(
    tool_call: LanguageModelFunction,
    name: str,
    message: str,
    url: str,
    tool_progress_reporter: ToolProgressReporter | None,
    crawler: CrawlerTypes,
) -> str:
    # Step 2: Crawl the URL
    if tool_progress_reporter:
        await tool_progress_reporter.notify_from_tool_call(
            name=name,
            message=message,
            tool_call=tool_call,
            state=ProgressState.RUNNING,
        )
    content = await crawler.crawl([url])  # type: ignore

    if not content:
        raise ValueError("No Markdown has been retrieved from the URL")

    markdown_content = content[0]

    return markdown_content


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
