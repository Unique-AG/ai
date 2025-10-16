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
            tool_info = {
                "name": tool_call_response.name,
                "info": tool_call_response.debug_info,
            }
            if loop_iteration_index is not None:
                tool_info["info"]["loop_iteration"] = loop_iteration_index
            self.debug_info["tools"].append(tool_info)

    def add(self, key: str, value: Any) -> None:
        self.debug_info = self.debug_info | {key: value}

    def get(self) -> dict[str, Any]:
        return self.debug_info
