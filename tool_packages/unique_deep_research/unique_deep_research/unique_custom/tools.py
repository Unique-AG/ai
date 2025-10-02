"""
LangGraph-compatible tools for Unique Custom Deep Research Engine
"""

import logging
from datetime import datetime
from typing import Any, List

import timeout_decorator
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from httpx import AsyncClient
from langchain_core.messages import ToolCall
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import Tool, tool
from markdownify import markdownify
from pydantic import BaseModel, Field
from unique_toolkit.agentic.history_manager.utils import transform_chunks_to_string
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogEvent,
    MessageLogUncitedReferences,
)
from unique_toolkit.content import ContentReference
from unique_toolkit.content.schemas import ContentSearchType
from unique_web_search.client_settings import get_google_search_settings
from unique_web_search.services.search_engine.google import GoogleConfig, GoogleSearch

from .utils import (
    get_content_service_from_config,
    get_engine_config,
    write_tool_message_log,
)

logger = logging.getLogger(__name__)


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")


# Tool parameter schemas for structured outputs
class ConductResearchArgs(BaseModel):
    """Arguments for delegating research to a specialized research agent."""

    research_topic: str = Field(
        description="The specific research instructions for the research agent to investigate"
    )


class ResearchCompleteArgs(BaseModel):
    """Arguments for signaling that research is complete."""

    reason: str = Field(description="Reason for completing research")


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
    short_progress_update: str = Field(
        description="The progress update and findings of the research"
    )


# LangGraph-compatible tool functions


@tool(args_schema=ConductResearchArgs)
def conduct_research(research_topic: str) -> str:
    """
    Delegate a specific research task to a specialized research agent.

    Use this tool when you need to conduct focused research on a specific topic.
    Each research agent will use available tools to gather comprehensive information.
    """
    return f"Research task delegated for topic: {research_topic}"


@tool(args_schema=ResearchCompleteArgs)
def research_complete(reason: str) -> str:
    """
    Signal that research is complete and provide a short reasoning.

    Use this tool when you have gathered sufficient information on the research topic.
    """
    return f"Research completed with reason: {reason}"


def research_complete_tool_called(tool_calls: list[ToolCall]) -> bool:
    """Check if the research complete tool was called."""
    return any(tc.get("name") == "research_complete" for tc in tool_calls)


@tool(args_schema=WebSearchArgs)
async def web_search(query: str, config: RunnableConfig, limit: int = 10) -> str:
    """
    Search the web for comprehensive, accurate, and trusted results.

    Useful for finding current information, news, and general knowledge
    from across the internet. Only returns snippets of the results.
    Should be followed up by web_fetch to get the complete content of the results.
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
        logger.warning("No search results found for query")
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
    Fetch and extract the full content from a specific web URL.

    Useful for getting detailed information from specific web pages
    that were found through search or are known to contain relevant content.
    """

    content, title = await crawl_url(AsyncClient(), url)

    # Crawl the URL
    if not content:
        logger.info(f"Unable to fetch content from: {url}")
        return f"Unable to fetch content from URL: {url}"

    write_tool_message_log(
        config,
        "Reading website",
        uncited_references=MessageLogUncitedReferences(
            data=[
                ContentReference(
                    name=title or url,
                    url=url,
                    sequence_number=0,
                    source="deep-research-citations",
                    source_id=url,
                )
            ]
        ),
    )

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
    You can use the InternalSearch tool to access internal company documentations, including information on policies, procedures, benefits, groups, financial details, and specific individuals
    If this tool can help answer your question, feel free to use it to search the internal knowledge base for more information.
    If possible always try to get information from the internal knowledge base with the InternalSearch tool before using expanding to other tools unless explicitly requested otherwise by the user.
    Use cases for the Internal Knowledge Search are:
    - User asks to work with a document: Most likely the document is uploaded to the chat and mentioned in a message and can be loaded with this tool
    - Policy and Procedure Verification: Use the internal search tool to find the most current company policies, procedures, or guidelines to ensure compliance and accuracy in responses.
    - Project-Specific Information: When answering questions related to ongoing projects or initiatives, use the internal search to access project documents, reports, or meeting notes for precise details.
    - Employee Directory and Contact Information: Utilize the internal search to locate contact details or organizational charts to facilitate communication and collaboration within the company.
    - Confidential and Proprietary Information: When dealing with sensitive topics that require proprietary knowledge or confidential data, use the internal search to ensure the information is sourced from secure and authorized company documents.
    """
    write_tool_message_log(
        config,
        "Searching the internal knowledge base",
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

    formatted_results, _ = transform_chunks_to_string(search_results, limit, None, True)
    return formatted_results


@tool(args_schema=InternalFetchArgs)
async def internal_fetch(
    content_id: str, config: RunnableConfig, offset: int = 0, limit: int = 50
) -> str:
    """
    Fetch and extract content from a specific internal document or knowledge base entry by its unique identifier.
    This tool is used to get the full content of a specific internal document or knowledge base entry by its unique identifier.

    This tool supports the internal search tool to get the full content of a specific internal document or knowledge base entry discovered by the internal search tool
    """
    logger.info("Reading internal knowledge base document")
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

    formatted_results, _ = transform_chunks_to_string(paginated_results, 0, None, True)

    if is_at_end:
        formatted_results += "\n\n<END_OF_CONTENT>"
    else:
        remaining_results = total_results - (offset + len(paginated_results))
        if remaining_results > 0:
            formatted_results += f"\n\n[{remaining_results:,} more results available - use offset {offset + len(paginated_results)} to continue]"
    write_tool_message_log(
        config,
        "Reading internal knowledge base document",
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
def think_tool(
    reflection: str, short_progress_update: str, config: RunnableConfig
) -> str:
    """
    Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search and fetch action to analyze results and plan next steps systematically.
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

    The short_progress_update is for the user to understand the progress of the research and should be a 1-2 sentence highlevel summary of new findings,
    and next steps to be displayed to the user that initiated the research so they can understand the progress of the research.
    Make sure it's valid markdown with a **bold** header and a short paragraph of text. Don't mention the deployment of the research tool in the short_progress_update.
    make it about what will be done. Keep it short and concise. Also don't directly reference technical stuff such as delegating to a research agent.

    Example:

    **Analyzing recent developments in crypto**
    I'm noticing that tokenized US Treasuries on public chains have surged in 2024-2025, surpassing $1B and later $2B, according to sources like 21.co and RWA trackers.
    There's also the launch of spot Bitcoin ETFs in the US in January 2024, marking a significant step in institutional adoption.

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps
        short_progress_update: The progress update and findings of the research
    Returns:
        Confirmation that reflection has been recorded
    """
    write_tool_message_log(
        config,
        short_progress_update,
    )
    return f"Reflection recorded: {reflection}"


# Helper function to get all available tools
def get_research_tools(config: RunnableConfig) -> List[Any]:
    """Get all research tools available to individual researchers."""
    tools = [
        think_tool,
        research_complete,
    ]

    # Get engine configuration to check which tools are enabled
    engine_config = get_engine_config(config)

    # Add web search tools if enabled
    if engine_config.enable_web_search:
        tools.extend([web_search, web_fetch])

    # Add internal search tools if enabled
    if engine_config.enable_internal_search:
        tools.extend([internal_search, internal_fetch])

    return tools


def get_supervisor_tools() -> List[Any]:
    """Get all tools available to the research supervisor."""
    return [conduct_research, research_complete, think_tool]


################# Web Crawler Helper Functions #################

unwanted_types = {
    "application/octet-stream",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/",
    "video/",
    "audio/",
}


async def crawl_url(client: AsyncClient, url: str) -> tuple[str, str | None]:
    headers = {"User-Agent": UserAgent().random}

    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
    except Exception:
        logger.warning(f"Site returned error {response.status_code}")
        return "Unable to crawl URL", None

    content_type = response.headers.get("content-type", "").lower().split(";")[0]

    if content_type in unwanted_types:
        return f"Content type {content_type} is not allowed", None

    content = response.text

    markdown = _markdownify_html_with_timeout(content, 10)

    return markdown, get_title(content)


def _markdownify_html_with_timeout(content: str, timeout: float) -> str:
    @timeout_decorator.timeout(timeout)
    def _markdownify_html(content: str) -> str:
        markdown = markdownify(
            content,
            heading_style="ATX",
        )
        return markdown

    try:
        return _markdownify_html(content)
    except Exception:
        return "Unable to markdownify HTML"


def get_title(text: str) -> str | None:
    soup = BeautifulSoup(text, "html.parser")
    title_tag = soup.title
    return title_tag.string.strip() if title_tag and title_tag.string else None


def format_tools_for_prompt(tools: list[Tool]) -> str:
    """
    Extract complete tool information for prompt injection.

    Returns formatted markdown string with:
    - Tool name
    - Full description
    - Parameter details with types and descriptions

    Args:
        tools: List of LangChain tool objects

    Returns:
        Formatted string ready for template injection
    """
    lines = []

    for tool_obj in tools:
        # Tool name (bold)
        lines.append(f"**{tool_obj.name}**")

        # Full description (preserve multi-line formatting)
        lines.append(tool_obj.description)

        # Extract parameter details using built-in .args property
        properties = tool_obj.args

        if properties:
            lines.append("Parameters:")
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")

                if param_desc:
                    lines.append(f"  - `{param_name}` ({param_type}): {param_desc}")
                else:
                    lines.append(f"  - `{param_name}` ({param_type})")

        lines.append("")  # Blank line between tools

    return "\n".join(lines)
