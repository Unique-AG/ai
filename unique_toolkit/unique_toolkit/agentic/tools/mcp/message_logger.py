import json
from typing import Any

from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.language_model.schemas import LanguageModelFunction


class MCPMessageLogger:
    """Handles all message logging and progress reporting for MCP tool execution.

    Mirrors the WebSearchMessageLogger pattern: owns message log state and
    provides high-level methods for each execution phase (executing, completed, failed).
    """

    def __init__(
        self,
        message_step_logger: MessageStepLogger,
        tool_progress_reporter: ToolProgressReporter | None,
        tool_display_name: str,
        input_schema: dict[str, Any],
        company_id: str,
    ):
        self._message_step_logger = message_step_logger
        self._tool_progress_reporter = tool_progress_reporter
        self._tool_display_name = tool_display_name
        self._input_schema = input_schema
        self._company_id = company_id

        self._current_message_log: MessageLog | None = None
        self._status = MessageLogStatus.RUNNING
        self._progress_message = ""

    async def executing(
        self,
        tool_call: LanguageModelFunction,
        arguments: dict[str, Any],
    ) -> None:
        self._progress_message = self._build_progress_message(
            "_Executing MCP tool_", arguments
        )
        self._status = MessageLogStatus.RUNNING
        self._propagate_message_log()
        await self._notify_progress_reporter(
            tool_call,
            f"Executing MCP tool: {self._tool_display_name}",
            ProgressState.RUNNING,
        )

    async def completed(
        self,
        tool_call: LanguageModelFunction,
        arguments: dict[str, Any],
    ) -> None:
        self._progress_message = self._build_progress_message(
            "_Completed MCP tool_", arguments
        )
        self._status = MessageLogStatus.COMPLETED
        self._propagate_message_log()
        await self._notify_progress_reporter(
            tool_call,
            f"MCP tool completed: {self._tool_display_name}",
            ProgressState.FINISHED,
        )

    async def failed(
        self,
        tool_call: LanguageModelFunction,
        error: str,
        arguments: dict[str, Any] | None = None,
    ) -> None:
        self._progress_message = self._build_progress_message(
            "_Failed executing MCP tool_", arguments or {}
        )
        self._status = MessageLogStatus.FAILED
        self._propagate_message_log()
        await self._notify_progress_reporter(
            tool_call,
            f"MCP tool failed: {error}",
            ProgressState.FAILED,
        )

    def _build_progress_message(
        self, status_text: str, arguments: dict[str, Any]
    ) -> str:
        if not feature_flags.enable_mcp_tool_params_display.is_enabled(
            self._company_id
        ):
            return status_text

        formatted_args = self.format_arguments_as_markdown(
            arguments, self._input_schema
        )
        if not formatted_args:
            return status_text
        return f"{status_text}\n{formatted_args}"

    async def _notify_progress_reporter(
        self,
        tool_call: LanguageModelFunction,
        message: str,
        state: ProgressState,
    ) -> None:
        if (
            self._tool_progress_reporter
            and not feature_flags.enable_new_answers_ui_un_14411.is_enabled(
                self._company_id
            )
        ):
            await self._tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=f"**{self._tool_display_name}**",
                message=message,
                state=state,
            )

    def _propagate_message_log(self) -> None:
        self._current_message_log = (
            self._message_step_logger.create_or_update_message_log(
                active_message_log=self._current_message_log,
                header=self._tool_display_name,
                progress_message=self._progress_message,
                status=self._status,
            )
        )

    @staticmethod
    def format_arguments_as_markdown(
        arguments: dict[str, Any],
        input_schema: dict[str, Any],
        max_value_length: int = 200,
    ) -> str:
        if not arguments:
            return ""

        schema_properties = input_schema.get("properties", {})
        lines = []

        for key, value in arguments.items():
            label = schema_properties.get(key, {}).get("description") or key
            formatted = MCPMessageLogger._format_value(value, max_value_length)
            lines.append(f"- **{label}**: {formatted}")

        return "\n".join(lines)

    @staticmethod
    def _format_value(value: Any, max_length: int = 200) -> str:
        if value is None:
            return "_empty_"
        if isinstance(value, bool):
            return f"`{str(value).lower()}`"
        if isinstance(value, (int, float)):
            return f"`{value}`"
        if isinstance(value, str):
            if len(value) > max_length:
                return f"`{value[:max_length]}...`"
            return f"`{value}`"
        if isinstance(value, (list, dict)):
            if not value:
                kind = "list" if isinstance(value, list) else "object"
                return f"_empty {kind}_"
            serialized = json.dumps(value, ensure_ascii=False)
            if len(serialized) > max_length:
                return f"`{serialized[:max_length]}...`"
            return f"`{serialized}`"
        serialized = str(value)
        if len(serialized) > max_length:
            return f"`{serialized[:max_length]}...`"
        return f"`{serialized}`"
