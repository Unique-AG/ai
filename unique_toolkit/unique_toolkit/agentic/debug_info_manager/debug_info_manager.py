from typing import Any

from unique_toolkit.agentic.tools.openai_builtin import OpenAICodeInterpreterTool
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.language_model.schemas import (
    LanguageModelStreamResponse,
    ResponsesLanguageModelStreamResponse,
)


class DebugInfoManager:
    def __init__(self):
        self.debug_info = {"tools": []}

    def extract_tool_debug_info(
        self,
        tool_call_responses: list[ToolCallResponse],
        loop_iteration_index: int | None = None,
    ) -> None:
        for tool_call_response in tool_call_responses:
            debug_info = (
                tool_call_response.debug_info.copy()
                if tool_call_response.debug_info
                else {}
            )
            tool_info: dict = {
                "name": tool_call_response.name,
                "info": debug_info,
            }
            if debug_info.get("mcp_server"):
                tool_info["mcp_server"] = debug_info["mcp_server"]
            if loop_iteration_index is not None:
                tool_info["info"]["loop_iteration"] = loop_iteration_index
            self.debug_info["tools"].append(tool_info)

    def extract_builtin_tool_debug_info(
        self,
        stream_response: LanguageModelStreamResponse,
        loop_iteration_index: int | None = None,
    ) -> None:
        self.debug_info["tools"].extend(
            _extract_tool_calls_from_stream_response(
                stream_response, loop_iteration_index
            )
        )

    def add(self, key: str, value: Any) -> None:
        self.debug_info = self.debug_info | {key: value}

    def get(self) -> dict[str, Any]:
        return self.debug_info


def _extract_tool_calls_from_stream_response(
    stream_response: LanguageModelStreamResponse,
    loop_iteration_index: int | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(stream_response, ResponsesLanguageModelStreamResponse):
        return []

    seen = set()
    tool_infos = []

    for code_interpreter_call in stream_response.code_interpreter_calls:
        if code_interpreter_call.id in seen:
            continue

        seen.add(code_interpreter_call.id)

        debug_info = OpenAICodeInterpreterTool.get_debug_info(code_interpreter_call)
        if loop_iteration_index is not None:
            debug_info["loop_iteration"] = loop_iteration_index

        tool_infos.append(
            {
                "name": OpenAIBuiltInToolName.CODE_INTERPRETER,
                "info": debug_info,
            }
        )

    return tool_infos
