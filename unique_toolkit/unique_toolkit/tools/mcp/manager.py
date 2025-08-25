import logging
from unique_toolkit.tools.mcp.models import MCPToolConfig, EnrichedMCPTool
from unique_toolkit.tools.schemas import ChatEvent, McpServer, McpTool
from unique_toolkit.tools.mcp.tool_wrapper import MCPToolWrapper
from unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter

class MCPManager:
    def __init__(self, mcp_servers: list[McpServer], event: ChatEvent, tool_progress_reporter: ToolProgressReporter):
        self._mcp_servers = mcp_servers
        self._event = event
        self._tool_progress_reporter = tool_progress_reporter

    def get_mcp_servers(self):
        return self._mcp_servers
    
    def get_mcp_server_by_id(self, id: str):
        return next((server for server in self._mcp_servers if server.id == id), None)
    
    def _enrich_tool_with_mcp_info(self, mcp_tool: McpTool, server: McpServer) -> EnrichedMCPTool:
        enriched_tool = type("EnrichedMcpTool", (), {})()

        # Copy all attributes from the original tool
        for attr in dir(mcp_tool):
            if not attr.startswith("_"):
                setattr(enriched_tool, attr, getattr(mcp_tool, attr))

        # Add server-specific attributes
        enriched_tool.server_id = server.id
        enriched_tool.server_name = server.name
        enriched_tool.server_system_prompt = getattr(
            server, "system_prompt", None
        )
        enriched_tool.server_user_prompt = getattr(server, "user_prompt", None)
        enriched_tool.mcp_source_id = server.id

        return enriched_tool

    def create_mcp_tool_wrapper(self, mcp_tool: EnrichedMCPTool, tool_progress_reporter: ToolProgressReporter) -> MCPToolWrapper:
        """Create MCP tool wrapper that behave like internal tools"""
        try:
            config = MCPToolConfig()
            wrapper = MCPToolWrapper(
                mcp_tool=mcp_tool,
                config=config,
                event=self._event,
                tool_progress_reporter=tool_progress_reporter,
            )
            return wrapper
        except Exception as e:
            logging.error(
                f"Error creating MCP tool wrapper for {mcp_tool.name}: {e}"
            )
            return None
        
    def get_all_mcp_tools(self, selected_by_user: list[str]) -> list[MCPToolWrapper]:
        selected_tools = []
        for server in self._mcp_servers:
            if hasattr(server, "tools") and server.tools:
                for tool in server.tools:
                    enriched_tool = self._enrich_tool_with_mcp_info(tool, server)
                    wrapper = self.create_mcp_tool_wrapper(enriched_tool, self._tool_progress_reporter)
                    if wrapper is not None:
                        selected_tools.append(wrapper)
        return selected_tools