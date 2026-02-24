"""
MCP tool definitions for the Claude Agent SDK integration.

This module will contain Python ports of Abi's Node MCP tool implementations
(PR #20429), using Unique's Python services instead of the Node equivalents:

- search_knowledge_base: wraps SearchService (port of Node searchKnowledgeBase)
- list_chat_files: wraps ContentService (port of Node listChatFiles)
- read_chat_file: wraps ContentService (port of Node readChatFile)
- web_search: wraps WebSearchService (optional — in BASE_ALLOWED_TOOLS)

Each tool is registered via the claude-agent-sdk @tool decorator or passed
as a create_sdk_mcp_server tools list. Tool signatures mirror the MCP schema
expected by the platform's mcp__unique_platform__* namespace.
"""
