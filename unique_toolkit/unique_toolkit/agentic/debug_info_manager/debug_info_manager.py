from unique_toolkit.agentic.tools.schemas import ToolCallResponse


class DebugInfoManager:
    def __init__(self):
        self.debug_info = {"tools": []}

    def extract_tool_debug_info(self, tool_call_responses: list[ToolCallResponse]):
        for tool_call_response in tool_call_responses:
            self.debug_info["tools"].append(
                {
                    "name": tool_call_response.name,
                    "data": tool_call_response.debug_info,
                    "loop_iteration": tool_call_response.loop_iteration + 1
                    if tool_call_response.loop_iteration is not None
                    else None,
                    "is_forced": tool_call_response.is_forced,
                    "is_exclusive": tool_call_response.is_exclusive,
                }
            )

    def add(self, key, value):
        self.debug_info = self.debug_info | {key: value}

    def get(self):
        return self.debug_info
