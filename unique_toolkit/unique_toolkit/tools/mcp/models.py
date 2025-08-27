from typing import Any, Dict, Optional
from unique_toolkit.app.schemas import McpServer
from unique_toolkit.tools.schemas import BaseToolConfig


class MCPTool:
    """Protocol defining the expected structure of an MCP tool."""

    name: str
    description: Optional[str]
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]
    annotations: Optional[Dict[str, Any]]
    title: Optional[str]
    icon: Optional[str]
    system_prompt: Optional[str]
    user_prompt: Optional[str]
    is_connected: bool


class MCPToolConfig(BaseToolConfig):
    """Configuration for MCP tools"""

    server_id: str
    server_name: str
    server_system_prompt: Optional[str] = None
    server_user_prompt: Optional[str] = None
    mcp_source_id: str
