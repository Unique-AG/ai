from typing import Any

from unique_toolkit.agentic.tools.schemas import ToolCallResponse


class DebugInfoManager:
    def __init__(self):
        self.debug_info = {"tools": []}

    def extract_tool_debug_info(
        self,
        tool_call_responses: list[ToolCallResponse],
        loop_iteration_index: int | None = None,
    ):
        for tool_call_response in tool_call_responses:
            debug_info = (
                tool_call_response.debug_info.copy()
                if tool_call_response.debug_info
                else {}
            )
            tool_info: dict[str, Any] = {
                "name": tool_call_response.name,
                "info": debug_info,
            }
            if debug_info.get("mcp_server"):
                tool_info["mcp_server"] = debug_info["mcp_server"]
            if loop_iteration_index is not None:
                tool_info["info"]["loop_iteration"] = loop_iteration_index
            self.debug_info["tools"].append(tool_info)

    def add(self, key: str, value: Any) -> None:
        self.debug_info = self.debug_info | {key: value}

    def get(self) -> dict[str, Any]:
        return self.debug_info
