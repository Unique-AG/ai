"""
Test suite for the MCP tools layer (mcp_tools.py).

All tests are CI-safe — no real API calls, no real SDK subprocess.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_agent_sdk import SdkMcpTool

from unique_toolkit.agentic.claude_agent.config import ClaudeAgentConfig
from unique_toolkit.agentic.claude_agent.mcp_tools import (
    _build_kb_search_tool,
    _build_platform_proxy_tools,
    _create_proxy_tool,
    build_unique_mcp_server,
)
from unique_toolkit.content.schemas import ContentChunk, ContentSearchType

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_content_chunk(text: str, key: str, index: int = 0) -> ContentChunk:
    return ContentChunk(
        id=f"cont_{'x' * 24}",
        text=text,
        order=index,
        key=key,
    )


def _make_mock_event(mcp_servers: list[Any] | None = None) -> MagicMock:
    event = MagicMock()
    event.user_id = "user-123"
    event.company_id = "company-456"
    event.payload.chat_id = "chat-789"
    event.payload.assistant_message.id = "msg-001"
    event.payload.mcp_servers = mcp_servers or []
    return event


def _make_mock_mcp_tool(
    name: str,
    description: str = "A tool",
    is_connected: bool = True,
    input_schema: dict[str, Any] | None = None,
) -> MagicMock:
    t = MagicMock()
    t.name = name
    t.description = description
    t.is_connected = is_connected
    t.input_schema = input_schema or {"type": "object", "properties": {}}
    return t


def _make_mock_mcp_server(tools: list[Any]) -> MagicMock:
    s = MagicMock()
    s.tools = tools
    return s


# ─────────────────────────────────────────────────────────────────────────────
# TestBuildKbSearchTool
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildKbSearchTool:
    def test_kb_search_returns_formatted_results(self) -> None:
        """Tool returns JSON with source_number, content, source for each chunk."""
        content_service = MagicMock()
        content_service.search_content_chunks.return_value = [
            _make_content_chunk("Interest rates rose sharply.", "report_2024.pdf", 0),
            _make_content_chunk("Inflation continued to decline.", "report_q3.pdf", 1),
        ]
        config = ClaudeAgentConfig()

        kb_tool = _build_kb_search_tool(content_service, config)
        assert isinstance(kb_tool, SdkMcpTool)
        assert kb_tool.name == "search_knowledge_base"

        result = asyncio.run(kb_tool.handler({"search_query": "interest rates"}))

        assert "content" in result
        assert len(result["content"]) == 1
        parsed = json.loads(result["content"][0]["text"])
        assert len(parsed) == 2
        assert parsed[0]["source_number"] == 0
        assert parsed[0]["content"] == "Interest rates rose sharply."
        assert parsed[0]["source"] == "report_2024.pdf"
        assert parsed[1]["source_number"] == 1
        assert parsed[1]["source"] == "report_q3.pdf"

    def test_kb_search_handles_empty_results(self) -> None:
        """Tool returns valid MCP result with empty JSON array when no chunks found."""
        content_service = MagicMock()
        content_service.search_content_chunks.return_value = []
        config = ClaudeAgentConfig()

        kb_tool = _build_kb_search_tool(content_service, config)
        result = asyncio.run(kb_tool.handler({"search_query": "obscure topic"}))

        assert "content" in result
        parsed = json.loads(result["content"][0]["text"])
        assert parsed == []

    def test_kb_search_handles_error_gracefully(self) -> None:
        """Tool catches exceptions and returns an error message instead of raising."""
        content_service = MagicMock()
        content_service.search_content_chunks.side_effect = RuntimeError("DB timeout")
        config = ClaudeAgentConfig()

        kb_tool = _build_kb_search_tool(content_service, config)
        result = asyncio.run(kb_tool.handler({"search_query": "anything"}))

        assert "content" in result
        text = result["content"][0]["text"]
        assert "Error searching knowledge base" in text
        assert "DB timeout" in text

    def test_kb_search_uses_config_search_type(self) -> None:
        """search_type from ClaudeAgentConfig is passed to content_service."""
        content_service = MagicMock()
        content_service.search_content_chunks.return_value = []
        config = ClaudeAgentConfig(search_type="VECTOR")

        kb_tool = _build_kb_search_tool(content_service, config)
        asyncio.run(kb_tool.handler({"search_query": "test"}))

        call_kwargs = content_service.search_content_chunks.call_args
        assert call_kwargs.args[1] == ContentSearchType.VECTOR

    def test_kb_search_falls_back_to_combined_for_unknown_type(self) -> None:
        """An unrecognised search_type string falls back to COMBINED without raising."""
        content_service = MagicMock()
        content_service.search_content_chunks.return_value = []
        config = ClaudeAgentConfig(search_type="UNSUPPORTED_TYPE")

        kb_tool = _build_kb_search_tool(content_service, config)
        asyncio.run(kb_tool.handler({"search_query": "test"}))
        call_kwargs = content_service.search_content_chunks.call_args
        assert call_kwargs.args[1] == ContentSearchType.COMBINED


# ─────────────────────────────────────────────────────────────────────────────
# TestBuildPlatformProxyTools
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildPlatformProxyTools:
    def test_proxy_tools_created_for_connected_platform_tools(self) -> None:
        """Returns one SdkMcpTool per connected platform tool."""
        tools = [
            _make_mock_mcp_tool("web_search"),
            _make_mock_mcp_tool("list_files"),
        ]
        event = _make_mock_event([_make_mock_mcp_server(tools)])

        proxies = _build_platform_proxy_tools(event)

        assert len(proxies) == 2
        names = {p.name for p in proxies}
        assert names == {"web_search", "list_files"}

    def test_proxy_tools_skip_disconnected_tools(self) -> None:
        """Tools with is_connected=False are excluded from the proxy list."""
        tools = [
            _make_mock_mcp_tool("web_search", is_connected=True),
            _make_mock_mcp_tool("broken_tool", is_connected=False),
        ]
        event = _make_mock_event([_make_mock_mcp_server(tools)])

        proxies = _build_platform_proxy_tools(event)

        assert len(proxies) == 1
        assert proxies[0].name == "web_search"

    def test_proxy_tools_skip_search_knowledge_base(self) -> None:
        """search_knowledge_base is skipped — we have a direct implementation."""
        tools = [
            _make_mock_mcp_tool("search_knowledge_base"),
            _make_mock_mcp_tool("web_search"),
        ]
        event = _make_mock_event([_make_mock_mcp_server(tools)])

        proxies = _build_platform_proxy_tools(event)

        assert len(proxies) == 1
        assert proxies[0].name == "web_search"

    def test_proxy_tools_empty_when_no_mcp_servers(self) -> None:
        """Returns empty list when the event has no mcp_servers."""
        event = _make_mock_event([])

        proxies = _build_platform_proxy_tools(event)

        assert proxies == []

    @pytest.mark.asyncio
    async def test_proxy_tool_calls_sdk_mcp_call_tool_async(self) -> None:
        """Proxy tool calls unique_sdk.MCP.call_tool_async with correct args."""
        mcp_tool = _make_mock_mcp_tool("web_search")
        event = _make_mock_event()

        mock_result = MagicMock()
        mock_result.content = [{"type": "text", "text": "search results here"}]

        with patch(
            "unique_toolkit.agentic.claude_agent.mcp_tools.unique_sdk.MCP.call_tool_async",
            new=AsyncMock(return_value=mock_result),
        ) as mock_call:
            proxy = _create_proxy_tool(event, mcp_tool)
            result = await proxy.handler({"query": "AI news"})

        mock_call.assert_called_once_with(
            user_id="user-123",
            company_id="company-456",
            name="web_search",
            messageId="msg-001",
            chatId="chat-789",
            arguments={"query": "AI news"},
        )
        assert result["content"][0]["text"] == "search results here"

    @pytest.mark.asyncio
    async def test_proxy_tool_returns_no_results_for_empty_content(self) -> None:
        """Proxy tool returns 'No results' fallback when SDK returns empty content."""
        mcp_tool = _make_mock_mcp_tool("web_search")
        event = _make_mock_event()

        mock_result = MagicMock()
        mock_result.content = []

        with patch(
            "unique_toolkit.agentic.claude_agent.mcp_tools.unique_sdk.MCP.call_tool_async",
            new=AsyncMock(return_value=mock_result),
        ):
            proxy = _create_proxy_tool(event, mcp_tool)
            result = await proxy.handler({})

        assert result["content"][0]["text"] == "No results"


# ─────────────────────────────────────────────────────────────────────────────
# TestBuildUniqueServer
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildUniqueServer:
    def test_build_unique_mcp_server_returns_sdk_config(self) -> None:
        """build_unique_mcp_server() returns a dict with the expected McpSdkServerConfig keys."""
        content_service = MagicMock()
        content_service.search_content_chunks.return_value = []
        config = ClaudeAgentConfig()
        event = _make_mock_event()

        result = build_unique_mcp_server(content_service, config, event)

        # McpSdkServerConfig is a TypedDict — check required keys instead of isinstance
        assert isinstance(result, dict)
        assert result.get("type") == "sdk"
        assert result.get("name") == "unique_platform"

    def test_build_unique_mcp_server_includes_kb_search(self) -> None:
        """The KB search tool is built with the correct name."""
        content_service = MagicMock()
        content_service.search_content_chunks.return_value = []
        config = ClaudeAgentConfig()

        kb_tool = _build_kb_search_tool(content_service, config)

        assert kb_tool.name == "search_knowledge_base"

    def test_build_unique_mcp_server_includes_proxy_tools(self) -> None:
        """Server includes proxy tools for all connected platform MCP tools."""
        content_service = MagicMock()
        content_service.search_content_chunks.return_value = []
        config = ClaudeAgentConfig()
        tools = [
            _make_mock_mcp_tool("web_search"),
            _make_mock_mcp_tool("read_file"),
        ]
        event = _make_mock_event([_make_mock_mcp_server(tools)])

        result = build_unique_mcp_server(content_service, config, event)

        assert isinstance(result, dict)
        assert result.get("type") == "sdk"
        proxies = _build_platform_proxy_tools(event)
        assert len(proxies) == 2
