"""
MCP tool definitions for the Claude Agent SDK integration.

Provides a single public function, build_unique_mcp_server(), that assembles
the unified in-process MCP server named "unique_platform". The server exposes:

1. search_knowledge_base — direct implementation calling ContentService.
2. Proxy tools for every connected platform MCP tool in
   event.payload.mcp_servers, forwarded via unique_sdk.MCP.call_tool_async().
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import unique_sdk
from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig

from unique_toolkit.content.schemas import ContentSearchType
from unique_toolkit.content.service import ContentService

from .config import ClaudeAgentConfig

if TYPE_CHECKING:
    from unique_toolkit.app.schemas import ChatEvent, McpTool


def build_unique_mcp_server(
    content_service: ContentService,
    claude_config: ClaudeAgentConfig,
    event: "ChatEvent",
) -> McpSdkServerConfig:
    """Build the unified in-process MCP server for Claude Agent.

    Creates an MCP server named "unique_platform" with:
    1. A direct search_knowledge_base tool (calls ContentService)
    2. Proxy tools for all platform MCP servers in event.payload.mcp_servers
    """
    tools: list[SdkMcpTool[Any]] = []

    tools.append(_build_kb_search_tool(content_service, claude_config))

    proxy_tools = _build_platform_proxy_tools(event)
    tools.extend(proxy_tools)

    return create_sdk_mcp_server(name="unique_platform", tools=tools)


def _build_kb_search_tool(
    content_service: ContentService,
    claude_config: ClaudeAgentConfig,
) -> SdkMcpTool[Any]:
    """Create the search_knowledge_base MCP tool backed by ContentService."""
    try:
        search_type = ContentSearchType[claude_config.search_type]
    except KeyError:
        search_type = ContentSearchType.COMBINED

    scope_ids = list(claude_config.scope_ids)

    @tool(
        "search_knowledge_base",
        "Search the knowledge base for relevant information. Returns numbered source chunks.",
        {"search_query": str},
    )
    async def search_knowledge_base(args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("search_query", "")
        try:
            chunks = await asyncio.to_thread(
                content_service.search_content_chunks,
                query,
                search_type,
                10,
                scope_ids=scope_ids or None,
            )
            results = [
                {
                    "source_number": i + 1,
                    "content": chunk.text,
                    "source": chunk.key or "unknown",
                }
                for i, chunk in enumerate(chunks)
            ]
            return {"content": [{"type": "text", "text": json.dumps(results)}]}
        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error searching knowledge base: {e}"}
                ]
            }

    return search_knowledge_base


def _build_platform_proxy_tools(event: "ChatEvent") -> list[SdkMcpTool[Any]]:
    """Wrap all connected platform MCP tools as proxy tools.

    Each tool forwards calls to unique_sdk.MCP.call_tool_async(), making any
    MCP server configured in the platform (web search, custom connectors, etc.)
    automatically available to Claude without per-tool implementation work.
    """
    proxy_tools: list[SdkMcpTool[Any]] = []
    mcp_servers = getattr(event.payload, "mcp_servers", []) or []

    for server in mcp_servers:
        for mcp_tool in server.tools:
            if mcp_tool.name == "search_knowledge_base":
                continue
            if not mcp_tool.is_connected:
                continue
            proxy_tools.append(_create_proxy_tool(event, mcp_tool))

    return proxy_tools


def _create_proxy_tool(event: "ChatEvent", mcp_tool: "McpTool") -> SdkMcpTool[Any]:
    """Create a proxy @tool that forwards calls to the platform via unique_sdk."""

    @tool(
        mcp_tool.name,
        mcp_tool.description or f"Platform tool: {mcp_tool.name}",
        mcp_tool.input_schema,
    )
    async def proxy_fn(args: dict[str, Any]) -> dict[str, Any]:
        result = await unique_sdk.MCP.call_tool_async(
            user_id=event.user_id,
            company_id=event.company_id,
            name=mcp_tool.name,
            messageId=event.payload.assistant_message.id,
            chatId=event.payload.chat_id,
            arguments=args,
        )
        content_items: list[dict[str, Any]] = []
        for item in result.content:
            if item.get("type") == "text":
                content_items.append({"type": "text", "text": item.get("text", "")})
            else:
                content_items.append({"type": "text", "text": json.dumps(item)})
        return {"content": content_items or [{"type": "text", "text": "No results"}]}

    return proxy_fn
