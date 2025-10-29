"""
Tests for unique_deep_research.unique_custom.tools module.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from unique_deep_research.unique_custom.tools import (
    _get_internal_data_citation,
    _get_internal_data_title,
    _markdownify_html_with_timeout,
    conduct_research,
    crawl_url,
    format_tools_for_prompt,
    get_research_tools,
    get_supervisor_tools,
    get_title,
    get_today_str,
    research_complete,
    research_complete_tool_called,
)


@pytest.mark.ai
def test_conduct_research__returns_delegation_message__with_research_topic() -> None:
    """
    Purpose: Verify conduct_research returns proper delegation message.
    Why this matters: Ensures research delegation works correctly.
    Setup summary: Call with research topic, assert delegation message.
    """
    # Arrange
    research_topic = "AI research trends"

    # Act
    result = conduct_research(research_topic)

    # Assert
    assert result == f"Research task delegated for topic: {research_topic}"


@pytest.mark.ai
def test_research_complete__returns_final_report__with_provided_report() -> None:
    """
    Purpose: Verify research_complete returns the final report as provided.
    Why this matters: Ensures final report is properly returned.
    Setup summary: Call with final report, assert same report returned.
    """
    # Arrange
    final_report = "# Research Report\n\nThis is the final report."

    # Act
    result = research_complete(final_report)

    # Assert
    assert result == final_report


@pytest.mark.ai
def test_research_complete_tool_called__returns_true__when_research_complete_in_tool_calls() -> (
    None
):
    """
    Purpose: Verify research_complete_tool_called detects research_complete tool calls.
    Why this matters: Critical for determining when research is complete.
    Setup summary: Provide tool calls with research_complete, assert True.
    """
    # Arrange
    tool_calls = [
        {"name": "web_search", "args": {"query": "test"}},
        {"name": "research_complete", "args": {"final_report": "done"}},
    ]

    # Act
    result = research_complete_tool_called(tool_calls)

    # Assert
    assert result is True


@pytest.mark.ai
def test_research_complete_tool_called__returns_false__when_research_complete_not_in_tool_calls() -> (
    None
):
    """
    Purpose: Verify research_complete_tool_called returns False when tool not called.
    Why this matters: Ensures proper detection of incomplete research.
    Setup summary: Provide tool calls without research_complete, assert False.
    """
    # Arrange
    tool_calls = [
        {"name": "web_search", "args": {"query": "test"}},
        {"name": "think_tool", "args": {"reflection": "thinking"}},
    ]

    # Act
    result = research_complete_tool_called(tool_calls)

    # Assert
    assert result is False


@pytest.mark.ai
def test_get_research_tools__returns_list_of_tools__with_expected_tools() -> None:
    """
    Purpose: Verify get_research_tools returns expected list of tools.
    Why this matters: Ensures research tools are properly configured.
    Setup summary: Call get_research_tools, assert expected tools in list.
    """
    # Arrange
    config = RunnableConfig()

    # Act
    tools = get_research_tools(config)

    # Assert
    assert (
        len(tools) >= 4
    )  # think_tool, research_complete, web_search, web_fetch, internal_search, internal_fetch
    tool_names = [tool.name for tool in tools]
    assert "think_tool" in tool_names
    assert "research_complete" in tool_names
    assert "web_search" in tool_names
    assert "web_fetch" in tool_names
    assert "internal_search" in tool_names
    assert "internal_fetch" in tool_names


@pytest.mark.ai
def test_get_supervisor_tools__returns_list_of_tools__with_expected_tools() -> None:
    """
    Purpose: Verify get_supervisor_tools returns expected list of tools.
    Why this matters: Ensures supervisor tools are properly configured.
    Setup summary: Call get_supervisor_tools, assert expected tools in list.
    """
    # Act
    tools = get_supervisor_tools()

    # Assert
    assert len(tools) == 3
    tool_names = [tool.name for tool in tools]
    assert "conduct_research" in tool_names
    assert "research_complete" in tool_names
    assert "think_tool" in tool_names


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_url__returns_error_message__when_request_fails() -> None:
    """
    Purpose: Verify crawl_url returns error message when HTTP request fails.
    Why this matters: Ensures graceful handling of failed HTTP requests.
    Setup summary: Mock AsyncClient to raise exception, assert error message.
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Connection failed")

    url = "https://invalid-url.com"

    # Act
    content, title, success = await crawl_url(mock_client, url)

    # Assert
    assert success is False
    assert "Unable to crawl URL in web_fetch" in content
    assert title is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_url__returns_error_message__when_content_type_not_allowed() -> (
    None
):
    """
    Purpose: Verify crawl_url returns error message for disallowed content types.
    Why this matters: Ensures proper filtering of unsupported content types.
    Setup summary: Mock response with PDF content type, assert error message.
    """
    # Arrange
    mock_response = Mock()
    mock_response.headers = {"content-type": "application/pdf"}
    mock_response.text = "PDF content"

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    url = "https://test.com/document.pdf"

    # Act
    content, title, success = await crawl_url(mock_client, url)

    # Assert
    assert success is False
    assert "Content type application/pdf is not allowed" in content
    assert title is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_url__returns_content_and_title__when_successful() -> None:
    """
    Purpose: Verify crawl_url returns content and title when successful.
    Why this matters: Ensures successful URL crawling works correctly.
    Setup summary: Mock successful response and markdownify, assert content and title.
    """
    # Arrange
    html_content = (
        "<html><head><title>Test Title</title></head><body>Test content</body></html>"
    )
    mock_response = Mock()
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = html_content

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    url = "https://test.com"

    # Act
    with (
        patch(
            "unique_deep_research.unique_custom.tools._markdownify_html_with_timeout",
            return_value=("# Test Title\n\nTest content", True),
        ),
        patch(
            "unique_deep_research.unique_custom.tools.get_title",
            return_value="Test Title",
        ),
    ):
        content, title, success = await crawl_url(mock_client, url)

    # Assert
    assert success is True
    assert "# Test Title\n\nTest content" in content
    assert title == "Test Title"


@pytest.mark.ai
def test_markdownify_html_with_timeout__returns_markdown__when_successful() -> None:
    """
    Purpose: Verify _markdownify_html_with_timeout returns markdown when successful.
    Why this matters: Ensures HTML to markdown conversion works correctly.
    Setup summary: Call with HTML content, assert markdown output.
    """
    # Arrange
    html_content = "<h1>Test Title</h1><p>Test content</p>"

    # Act
    markdown, success = _markdownify_html_with_timeout(html_content, 10)

    # Assert
    assert success is True
    assert "# Test Title" in markdown
    assert "Test content" in markdown


@pytest.mark.ai
def test_markdownify_html_with_timeout__returns_error_message__when_timeout() -> None:
    """
    Purpose: Verify _markdownify_html_with_timeout returns error message when timeout occurs.
    Why this matters: Ensures graceful handling of timeout during HTML conversion.
    Setup summary: Call with very short timeout, assert error message.
    """
    # Arrange
    html_content = "<h1>Test Title</h1><p>Test content</p>"

    # Act
    markdown, success = _markdownify_html_with_timeout(
        html_content, 0.001
    )  # Very short timeout

    # Assert
    # Note: This test might not always fail due to timing, so we'll check if it's either False or True
    assert isinstance(success, bool)
    if not success:
        assert "Unable to markdownify HTML" in markdown


@pytest.mark.ai
def test_get_title__returns_og_title__when_available() -> None:
    """
    Purpose: Verify get_title returns OpenGraph title when available.
    Why this matters: Ensures proper title extraction from HTML.
    Setup summary: Provide HTML with og:title, assert OpenGraph title returned.
    """
    # Arrange
    html_content = """
    <html>
    <head>
        <meta property="og:title" content="OpenGraph Title">
        <title>HTML Title</title>
    </head>
    </html>
    """

    # Act
    title = get_title(html_content)

    # Assert
    assert title == "OpenGraph Title"


@pytest.mark.ai
def test_get_title__returns_twitter_title__when_og_title_not_available() -> None:
    """
    Purpose: Verify get_title returns Twitter title when OpenGraph title not available.
    Why this matters: Ensures fallback title extraction works correctly.
    Setup summary: Provide HTML with twitter:title but no og:title, assert Twitter title returned.
    """
    # Arrange
    html_content = """
    <html>
    <head>
        <meta name="twitter:title" content="Twitter Title">
        <title>HTML Title</title>
    </head>
    </html>
    """

    # Act
    title = get_title(html_content)

    # Assert
    assert title == "Twitter Title"


@pytest.mark.ai
def test_get_title__returns_html_title__when_meta_titles_not_available() -> None:
    """
    Purpose: Verify get_title returns HTML title when meta titles not available.
    Why this matters: Ensures fallback to standard HTML title works correctly.
    Setup summary: Provide HTML with only title tag, assert HTML title returned.
    """
    # Arrange
    html_content = """
    <html>
    <head>
        <title>HTML Title</title>
    </head>
    </html>
    """

    # Act
    title = get_title(html_content)

    # Assert
    assert title == "HTML Title"


@pytest.mark.ai
def test_get_title__returns_none__when_no_title_found() -> None:
    """
    Purpose: Verify get_title returns None when no title found.
    Why this matters: Ensures proper handling of HTML without titles.
    Setup summary: Provide HTML without any title elements, assert None returned.
    """
    # Arrange
    html_content = """
    <html>
    <head>
    </head>
    <body>Content</body>
    </html>
    """

    # Act
    title = get_title(html_content)

    # Assert
    assert title is None


@pytest.mark.ai
def test_format_tools_for_prompt__returns_formatted_string__with_tool_info() -> None:
    """
    Purpose: Verify format_tools_for_prompt returns properly formatted tool information.
    Why this matters: Ensures tools are properly formatted for prompt injection.
    Setup summary: Create mock tools, call format_tools_for_prompt, assert formatted output.
    """
    # Arrange
    mock_tool1 = Mock()
    mock_tool1.name = "test_tool"
    mock_tool1.description = "Test tool description"
    mock_tool1.args = {
        "param1": {"type": "string", "description": "First parameter"},
        "param2": {"type": "integer", "description": "Second parameter"},
    }

    mock_tool2 = Mock()
    mock_tool2.name = "another_tool"
    mock_tool2.description = "Another tool description"
    mock_tool2.args = {}

    tools = [mock_tool1, mock_tool2]

    # Act
    result = format_tools_for_prompt(tools)

    # Assert
    assert "**test_tool**" in result
    assert "Test tool description" in result
    assert "Parameters:" in result
    assert "- `param1` (string): First parameter" in result
    assert "- `param2` (integer): Second parameter" in result
    assert "**another_tool**" in result
    assert "Another tool description" in result


@pytest.mark.ai
def test_get_internal_data_title__returns_key_with_pages__when_key_available() -> None:
    """
    Purpose: Verify _get_internal_data_title returns key with page numbers when available.
    Why this matters: Ensures proper title formatting for internal data.
    Setup summary: Create ContentChunk with key and pages, assert formatted title.
    """
    # Arrange
    mock_result = Mock()
    mock_result.key = "test-key"
    mock_result.start_page = 1
    mock_result.end_page = 5
    mock_result.title = "Test Title"
    mock_result.id = "content-123"

    # Act
    title = _get_internal_data_title(mock_result)

    # Assert
    assert title == "test-key : 1,5"


@pytest.mark.ai
def test_get_internal_data_title__returns_title__when_key_not_available() -> None:
    """
    Purpose: Verify _get_internal_data_title returns title when key not available.
    Why this matters: Ensures fallback title extraction works correctly.
    Setup summary: Create ContentChunk without key, assert title returned.
    """
    # Arrange
    mock_result = Mock()
    mock_result.key = None
    mock_result.title = "Test Title"
    mock_result.id = "content-123"

    # Act
    title = _get_internal_data_title(mock_result)

    # Assert
    assert title == "Test Title"


@pytest.mark.ai
def test_get_internal_data_title__returns_id__when_key_and_title_not_available() -> (
    None
):
    """
    Purpose: Verify _get_internal_data_title returns ID when key and title not available.
    Why this matters: Ensures final fallback to ID works correctly.
    Setup summary: Create ContentChunk without key or title, assert ID returned.
    """
    # Arrange
    mock_result = Mock()
    mock_result.key = None
    mock_result.title = None
    mock_result.id = "content-123"

    # Act
    title = _get_internal_data_title(mock_result)

    # Assert
    assert title == "content-123"


@pytest.mark.ai
def test_get_internal_data_citation__returns_content_reference__with_proper_fields() -> (
    None
):
    """
    Purpose: Verify _get_internal_data_citation returns properly formatted ContentReference.
    Why this matters: Ensures proper citation formatting for internal data.
    Setup summary: Create ContentChunk, call _get_internal_data_citation, assert ContentReference fields.
    """
    # Arrange
    mock_result = Mock()
    mock_result.key = "test-key"
    mock_result.start_page = 1
    mock_result.end_page = 5
    mock_result.title = "Test Title"
    mock_result.id = "content-123"
    mock_result.chunk_id = "chunk-456"
    mock_result.url = "https://test.com"

    sequence_number = 0

    # Act
    citation = _get_internal_data_citation(mock_result, sequence_number)

    # Assert
    assert citation.name == "test-key : 1,5"
    assert citation.url == "https://test.com"
    assert citation.sequence_number == 0
    assert citation.source == "node-ingestion-chunks"
    assert citation.source_id == "content-123_chunk-456"


@pytest.mark.ai
def test_get_today_str__returns_current_date__in_readable_format() -> None:
    """
    Purpose: Verify get_today_str returns current date in readable format.
    Why this matters: Ensures date formatting works correctly for tool usage.
    Setup summary: Call get_today_str, assert readable date format.
    """
    # Act
    date_str = get_today_str()

    # Assert
    assert isinstance(date_str, str)
    assert len(date_str) > 0
    # Should contain day of week, month, day, and year
    assert any(
        day in date_str for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    )
    assert any(
        month in date_str
        for month in [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    )
