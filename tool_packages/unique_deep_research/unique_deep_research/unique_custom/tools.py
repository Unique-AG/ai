"""
LangGraph-compatible tools for Unique Custom Deep Research Engine
"""

import logging
from datetime import datetime
from typing import Any, List

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from unique_toolkit.chat.schemas import MessageLogStatus
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


class WebFetchArgs(BaseModel):
    """Arguments for web fetch tool."""

    url: str = Field(description="URL to fetch content from")


class InternalSearchArgs(BaseModel):
    """Arguments for internal search tool."""

    query: str = Field(description="Query to search internal knowledge base")


class InternalFetchArgs(BaseModel):
    """Arguments for internal fetch tool."""

    content_id: str = Field(description="Content ID to fetch from internal system")


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
async def web_search(query: str, config: RunnableConfig) -> str:
    """
    Search the web for comprehensive, accurate, and trusted results.

    Useful for finding current information, news, and general knowledge
    from across the internet.
    """
    try:
        write_tool_message_log(config, f"Searching the web for: {query}")

        # Check if Google Search is configured
        google_settings = get_google_search_settings()

        if not google_settings.is_configured:
            logger.warning("Google Search not configured")
            write_tool_message_log(
                config, "Google Search not configured", MessageLogStatus.FAILED
            )
            return f"Web search not configured. Query was: '{query}'. Please configure Google Search API credentials."

        # Create Google search configuration and service
        google_config = GoogleConfig(fetch_size=10)
        google_search = GoogleSearch(google_config)

        # Perform the search
        search_results = await google_search.search(query)

        if not search_results:
            write_tool_message_log(config, f"No search results found for: {query}")
            return f"No search results found for query: '{query}'"

        # Format results for LangGraph
        formatted_results = []
        for i, result in enumerate(search_results[:10], 1):
            formatted_results.append(
                f"{i}. {result.title}\n   URL: {result.url}\n   Snippet: {result.snippet}\n"
            )

        write_tool_message_log(
            config, f"Found {len(search_results)} search results for: {query}"
        )
        return f"Web search results for '{query}':\n\n" + "\n".join(formatted_results)

    except Exception as e:
        logger.error(f"Error in web_search: {e}")
        write_tool_message_log(
            config, f"Error searching for: {query} - {str(e)}", MessageLogStatus.FAILED
        )
        return f"Error performing web search for '{query}': {str(e)}"


@tool(args_schema=WebFetchArgs)
async def web_fetch(url: str, config: RunnableConfig) -> str:
    """
    Fetch and extract content from a specific web URL.

    Useful for getting detailed information from specific web pages
    that were found through search or are known to contain relevant content.
    """
    try:
        write_tool_message_log(config, f"Fetching content from: {url}")

        # Create basic crawler configuration
        crawler_config = BasicCrawlerConfig(
            timeout=30,  # 30 second timeout
            max_concurrent_requests=1,  # Single request
        )

        # Create crawler instance
        crawler = BasicCrawler(crawler_config)

        # Crawl the URL
        results = await crawler.crawl([url])

        if not results or not results[0]:
            write_tool_message_log(
                config, f"Unable to fetch content from: {url}", MessageLogStatus.FAILED
            )
            return f"Unable to fetch content from URL: {url}"

        content = results[0]

        # Check if the content indicates an error
        if "An expected error occurred" in content or "Unable to crawl URL" in content:
            write_tool_message_log(
                config, f"Error fetching content from: {url}", MessageLogStatus.FAILED
            )
            return f"Error fetching content from {url}: {content}"

        # Truncate if too long (keep first 10000 characters)
        content_length = len(content)
        if content_length > 10000:
            content = content[:10000] + "\n\n[Content truncated...]"

        write_tool_message_log(
            config, f"Successfully fetched {content_length} characters from: {url}"
        )
        return f"Content from {url}:\n\n{content}"

    except Exception as e:
        logger.error(f"Error in web_fetch for URL {url}: {e}")
        write_tool_message_log(
            config,
            f"Error fetching content from: {url} - {str(e)}",
            MessageLogStatus.FAILED,
        )
        return f"Error fetching content from {url}: {str(e)}"


@tool(args_schema=InternalSearchArgs)
async def internal_search(query: str, config: RunnableConfig) -> str:
    """
    Search internal knowledge base using ContentService.

    Searches through internal documents, knowledge bases, and previously
    indexed content to find relevant information for research.
    """
    write_tool_message_log(config, f"Searching internal knowledge base for: {query}")
    content_service = get_content_service_from_config(config)

    # Use ContentService to search internal content
    search_results = await content_service.search_content_chunks_async(
        search_string=query,
        search_type=ContentSearchType.COMBINED,
        limit=100,
        score_threshold=0,
    )

    if not search_results:
        write_tool_message_log(config, f"No internal results found for: {query}")
        return f"No internal search results found for query: '{query}'"

    formatted_results = transform_chunks_to_string(search_results, 10, None, True)
    write_tool_message_log(
        config, f"Found {len(search_results)} internal results for: {query}"
    )
    return formatted_results


@tool(args_schema=InternalFetchArgs)
async def internal_fetch(content_id: str, config: RunnableConfig) -> str:
    """
    Fetch internal content by ID using ContentService.

    Retrieves the full content of a specific internal document or
    knowledge base entry by its unique identifier.
    """
    write_tool_message_log(
        config, f"Fetching internal knowledge base for: {content_id}"
    )
    content_service = get_content_service_from_config(config)

    # TODO: Metadata filter review
    search_results = await content_service.search_content_chunks_async(
        search_string=" ",  # Dummy search string
        search_type=ContentSearchType.COMBINED,
        limit=100,
        score_threshold=0,
        content_ids=[content_id],
    )

    if not search_results:
        write_tool_message_log(config, f"No internal results found for: {content_id}")
        return f"No internal fetch results found for content ID: '{content_id}'"

    formatted_results = transform_chunks_to_string(search_results, 0, None, True)
    write_tool_message_log(config, f"Successfully fetched content for ID: {content_id}")
    return formatted_results


@tool(args_schema=ThinkArgs)
def think_tool(reflection: str) -> str:
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
    return f"Reflection recorded: {reflection}"


# Helper function to get all available tools
def get_research_tools() -> List[Any]:
    """Get all research tools available to individual researchers."""
    return [web_search, web_fetch, internal_search, internal_fetch, think_tool]


def get_supervisor_tools() -> List[Any]:
    """Get all tools available to the research supervisor."""
    return [ConductResearch, ResearchComplete, think_tool]
