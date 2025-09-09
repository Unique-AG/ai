"""
LangGraph-compatible tools for Unique Custom Deep Research Engine
"""

import logging
from datetime import datetime
from typing import Any, List

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogEvent,
    MessageLogUncitedReferences,
)
from unique_toolkit.content import ContentReference
from unique_toolkit.content.schemas import ContentSearchType
from unique_toolkit.history_manager.utils import transform_chunks_to_string
from unique_web_search.client_settings import get_google_search_settings
from unique_web_search.services.preprocessing.crawlers.basic import (
    BasicCrawler,
    BasicCrawlerConfig,
)
from unique_web_search.services.search_engine.google import GoogleConfig, GoogleSearch

from .utils import get_content_service_from_config, write_tool_message_log

logger = logging.getLogger(__name__)


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")


# Tool parameter schemas for structured outputs
class ConductResearchArgs(BaseModel):
    """Arguments for delegating research to a specialized research agent."""

    research_topic: str = Field(
        description="The specific research topic or question to investigate"
    )


class ResearchCompleteArgs(BaseModel):
    """Arguments for signaling that research is complete."""

    summary: str = Field(description="Final summary of research findings")
    sources: List[str] = Field(default_factory=list, description="List of sources used")


class WebSearchArgs(BaseModel):
    """Arguments for web search tool."""

    query: str = Field(description="Search query to find relevant information")
    limit: int = Field(
        description="Limit of results to fetch from web", default=50, le=100, ge=1
    )


class WebFetchArgs(BaseModel):
    """Arguments for web fetch tool."""

    url: str = Field(description="URL to fetch content from")
    offset: int = Field(description="Result offset to fetch from web", default=0, ge=0)
    character_limit: int = Field(
        description="Limit of characters to fetch from web page",
        default=10_000,
        le=100_000,
        ge=1_000,
    )


class InternalSearchArgs(BaseModel):
    """Arguments for internal search tool."""

    query: str = Field(description="Query to search internal knowledge base")
    limit: int = Field(
        description="Limit of results to fetch from internal system",
        default=50,
        le=100,
        ge=1,
    )


class InternalFetchArgs(BaseModel):
    """Arguments for internal fetch tool."""

    content_id: str = Field(description="Content ID to fetch from internal system")
    offset: int = Field(
        description="Result offset to fetch from internal system", default=0, ge=0
    )
    limit: int = Field(
        description="Limit of results to fetch from internal system",
        default=50,
        le=100,
        ge=1,
    )


class ThinkArgs(BaseModel):
    """Arguments for strategic thinking tool."""

    reflection: str = Field(
        description="Detailed reflection on research progress, findings, gaps, and next steps"
    )


# LangGraph-compatible tool functions


@tool(args_schema=ConductResearchArgs)
def ConductResearch(research_topic: str) -> str:
    """
    Delegate a specific research task to a specialized research agent.

    Use this tool when you need to conduct focused research on a specific topic.
    Each research agent will use available tools to gather comprehensive information.
    """
    return f"Research task delegated for topic: {research_topic}"


@tool(args_schema=ResearchCompleteArgs)
def ResearchComplete(summary: str, sources: List[str] = []) -> str:
    """
    Signal that research is complete and provide a comprehensive summary.

    Use this tool when you have gathered sufficient information to answer
    the research question comprehensively.
    """
    sources = sources or []
    sources_text = f" Sources: {', '.join(sources)}" if sources else ""
    return f"Research completed. Summary: {summary}{sources_text}"


# Research tools using unique-web-search implementations


@tool(args_schema=WebSearchArgs)
async def web_search(query: str, config: RunnableConfig, limit: int = 10) -> str:
    """
    Search the web for comprehensive, accurate, and trusted results.

    Useful for finding current information, news, and general knowledge
    from across the internet.
    """
    write_tool_message_log(
        config,
        "Searching the web",
        details=MessageLogDetails(data=[MessageLogEvent(type="WebSearch", text=query)]),
    )
    google_settings = get_google_search_settings()

    if not google_settings.is_configured:
        logger.error("Google Search not configured")
        raise ValueError("Google Search not configured")

    # Create Google search configuration and service
    google_config = GoogleConfig(fetch_size=limit)
    google_search = GoogleSearch(google_config)

    # Perform the search
    search_results = await google_search.search(query)

    if not search_results:
        logger.warning(f"No search results found for: {query}")
        return f"No search results found for query: '{query}'"

    # Format results for LangGraph
    formatted_results = []
    for i, result in enumerate(search_results[:limit], 1):
        formatted_results.append(
            f"{i}. {result.title}\n   URL: {result.url}\n   Snippet: {result.snippet}\n"
        )
    return f"Web search results for '{query}':\n\n" + "\n".join(formatted_results)


@tool(args_schema=WebFetchArgs)
async def web_fetch(
    url: str, config: RunnableConfig, offset: int = 0, character_limit: int = 10_000
) -> str:
    """
    Fetch and extract content from a specific web URL.

    Useful for getting detailed information from specific web pages
    that were found through search or are known to contain relevant content.
    """
    write_tool_message_log(
        config,
        "Reviewing Web Sources",
        uncited_references=MessageLogUncitedReferences(
            data=[
                ContentReference(
                    name=url,
                    url=url,
                    sequence_number=0,
                    source="deep-research-citations",
                    source_id=url,
                )
            ]
        ),
    )
    # Create basic crawler configuration
    crawler_config = BasicCrawlerConfig()

    # Create crawler instance
    crawler = BasicCrawler(crawler_config)

    # Crawl the URL
    results = await crawler.crawl([url])

    if not results or not results[0]:
        # TODO: Should this be shown to the user?
        logger.info(f"Unable to fetch content from: {url}")
        return f"Unable to fetch content from URL: {url}"

    content = results[0]

    # Apply offset and character limit
    original_content_length = len(content)

    # If offset is beyond content, get the tail within character_limit
    if offset >= original_content_length:
        # Get the last character_limit characters from original content
        tail_start = max(0, original_content_length - character_limit)
        tail_content = content[tail_start:]
        tail_content = f"[Showing tail of content from position {tail_start:,}]\n\n{tail_content}\n\n<END_OF_CONTENT>"
        return f"Content from {url}:\n\n{tail_content}"

    # Apply normal offset
    if offset > 0:
        content = content[offset:]

    # Apply character limit and add appropriate markers
    current_content_length = len(content)

    if current_content_length > character_limit:
        remaining_chars = current_content_length - character_limit
        content = (
            content[:character_limit]
            + f"\n\n[Content truncated... {remaining_chars:,} characters remaining]"
        )
    elif current_content_length <= character_limit:
        # We're showing all available content (either from offset or from start)
        content = content + "\n\n<END_OF_CONTENT>"

    return f"Content from {url}:\n\n{content}"


@tool(args_schema=InternalSearchArgs)
async def internal_search(query: str, config: RunnableConfig, limit: int = 50) -> str:
    """
    Search internal knowledge base using ContentService.

    Searches through internal documents, knowledge bases, and previously
    indexed content to find relevant information for research.
    """
    write_tool_message_log(
        config,
        "Searching internal knowledge base",
        details=MessageLogDetails(
            data=[MessageLogEvent(type="InternalSearch", text=query)]
        ),
    )
    content_service = get_content_service_from_config(config)

    # Use ContentService to search internal content
    search_results = await content_service.search_content_chunks_async(
        search_string=query,
        search_type=ContentSearchType.COMBINED,
        limit=limit,
        score_threshold=0,
    )
    logger.info(f"Found {len(search_results)} internal results")
    if not search_results:
        logger.info("No internal results found")
        return f"No internal search results found for query: '{query}'"

    formatted_results = transform_chunks_to_string(search_results, limit, None, True)
    return formatted_results


@tool(args_schema=InternalFetchArgs)
async def internal_fetch(
    content_id: str, config: RunnableConfig, offset: int = 0, limit: int = 50
) -> str:
    """
    Fetch internal content by ID using ContentService.

    Retrieves the full content of a specific internal document or
    knowledge base entry by its unique identifier.
    """
    logger.info("Fetching from internal knowledge base")
    content_service = get_content_service_from_config(config)

    temp_metadata_filter = content_service._metadata_filter
    content_service._metadata_filter = None
    search_results = await content_service.search_content_chunks_async(
        search_string=" ",  # Dummy search string
        search_type=ContentSearchType.COMBINED,
        limit=limit,  # Get enough results to support offset
        score_threshold=0,
        content_ids=[content_id],
    )
    content_service._metadata_filter = temp_metadata_filter

    if not search_results:
        logger.info("No internal results found")
        return f"No internal fetch results found for content ID: '{content_id}'"

    # Apply offset and limit to results
    total_results = len(search_results)

    # Get the paginated results, even if offset is at or beyond the end
    paginated_results = search_results[offset : offset + limit]

    # Check if we're at the end of results
    is_at_end = offset + len(paginated_results) >= total_results

    if len(paginated_results) == 0 and offset >= total_results:
        return f"No more results for content ID: '{content_id}'\n\n<END_OF_CONTENT>\n\nNote: Offset {offset} is at or beyond total results ({total_results:,})"

    formatted_results = transform_chunks_to_string(paginated_results, 0, None, True)

    if is_at_end:
        formatted_results += "\n\n<END_OF_CONTENT>"
    else:
        remaining_results = total_results - (offset + len(paginated_results))
        if remaining_results > 0:
            formatted_results += f"\n\n[{remaining_results:,} more results available - use offset {offset + len(paginated_results)} to continue]"
    write_tool_message_log(
        config,
        "Reviewing Web Sources",
        uncited_references=MessageLogUncitedReferences(
            data=[
                ContentReference(
                    name=search_results[0].title or content_id,
                    url=search_results[0].url or "",
                    sequence_number=0,
                    source="deep-research-citations",
                    source_id=search_results[0].id,
                )
            ]
        ),
    )
    return formatted_results


@tool(args_schema=ThinkArgs)
def think_tool(reflection: str, config: RunnableConfig) -> str:
    """
    Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection has been recorded
    """
    write_tool_message_log(
        config,
        reflection,
    )
    return f"Reflection recorded: {reflection}"


# Helper function to get all available tools
def get_research_tools() -> List[Any]:
    """Get all research tools available to individual researchers."""
    return [web_search, web_fetch, internal_search, internal_fetch, think_tool]


def get_supervisor_tools() -> List[Any]:
    """Get all tools available to the research supervisor."""
    return [ConductResearch, ResearchComplete, think_tool]
