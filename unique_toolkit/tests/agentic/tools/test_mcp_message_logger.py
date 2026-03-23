"""
Test suite for MCPMessageLogger class.

This test suite validates:
1. Static markdown formatting of tool arguments
2. Value formatting for different types
3. Message log propagation in executing/completed/failed states
4. Feature-flag-gated parameter display
5. Progress reporter notifications gated by the answers UI flag
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from unique_toolkit.agentic.tools.mcp.message_logger import MCPMessageLogger
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.language_model.schemas import LanguageModelFunction


FEATURE_FLAGS_PATH = "unique_toolkit.agentic.tools.mcp.message_logger.feature_flags"

INPUT_SCHEMA_WITH_DESCRIPTIONS = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query"},
        "limit": {"type": "integer", "description": "Result limit"},
    },
    "required": ["query"],
}

INPUT_SCHEMA_WITHOUT_DESCRIPTIONS = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "limit": {"type": "integer"},
    },
}


@pytest.fixture
def mock_message_step_logger() -> Mock:
    logger = Mock()
    mock_message_log = Mock(spec=MessageLog)
    logger.create_or_update_message_log.return_value = mock_message_log
    return logger


@pytest.fixture
def mock_tool_progress_reporter() -> Mock:
    reporter = Mock(spec=ToolProgressReporter)
    reporter.notify_from_tool_call = AsyncMock()
    return reporter


@pytest.fixture
def mock_tool_call() -> LanguageModelFunction:
    return LanguageModelFunction(
        id="call_123",
        name="test_tool",
        arguments={"query": "hello"},
    )


def _make_logger(
    message_step_logger: Mock,
    tool_progress_reporter: Mock | None = None,
    input_schema: dict | None = None,
    company_id: str = "company_456",
) -> MCPMessageLogger:
    return MCPMessageLogger(
        message_step_logger=message_step_logger,
        tool_progress_reporter=tool_progress_reporter,
        tool_display_name="Test Tool",
        input_schema=input_schema or INPUT_SCHEMA_WITH_DESCRIPTIONS,
        company_id=company_id,
    )


class TestFormatArgumentsAsMarkdown:
    """Tests for the static format_arguments_as_markdown method."""

    @pytest.mark.ai
    def test_renders_descriptions_as_labels(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": "hello world", "limit": 10},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
        )
        assert "- **Search query**: `hello world`" in result
        assert "- **Result limit**: `10`" in result

    @pytest.mark.ai
    def test_falls_back_to_key_name__when_no_description(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": "hello", "limit": 5},
            INPUT_SCHEMA_WITHOUT_DESCRIPTIONS,
        )
        assert "- **query**: `hello`" in result
        assert "- **limit**: `5`" in result

    @pytest.mark.ai
    def test_falls_back_to_key_name__when_key_not_in_schema(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"unknown_param": "value"},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
        )
        assert "- **unknown_param**: `value`" in result

    @pytest.mark.ai
    def test_returns_empty__when_no_arguments(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {}, INPUT_SCHEMA_WITH_DESCRIPTIONS
        )
        assert result == ""

    @pytest.mark.ai
    def test_truncates_long_strings(self) -> None:
        long_value = "x" * 300
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": long_value},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
            max_value_length=50,
        )
        assert "..." in result
        assert len(result) < 300

    @pytest.mark.ai
    def test_handles_nested_objects(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": {"nested": "value"}},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
        )
        assert '`{"nested": "value"}`' in result

    @pytest.mark.ai
    def test_handles_arrays(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": [1, 2, 3]},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
        )
        assert "`[1, 2, 3]`" in result

    @pytest.mark.ai
    def test_handles_empty_list(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": []},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
        )
        assert "_empty list_" in result

    @pytest.mark.ai
    def test_handles_empty_dict(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": {}},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
        )
        assert "_empty object_" in result

    @pytest.mark.ai
    def test_handles_none_value(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": None},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
        )
        assert "_empty_" in result

    @pytest.mark.ai
    def test_handles_boolean_values(self) -> None:
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": True},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
        )
        assert "`true`" in result

    @pytest.mark.ai
    def test_truncates_long_nested_objects(self) -> None:
        large_dict = {"key": "v" * 300}
        result = MCPMessageLogger.format_arguments_as_markdown(
            {"query": large_dict},
            INPUT_SCHEMA_WITH_DESCRIPTIONS,
            max_value_length=50,
        )
        assert "..." in result


class TestFormatValue:
    """Tests for the static _format_value method."""

    @pytest.mark.ai
    def test_format_value__string(self) -> None:
        assert MCPMessageLogger._format_value("hello") == "`hello`"

    @pytest.mark.ai
    def test_format_value__int(self) -> None:
        assert MCPMessageLogger._format_value(42) == "`42`"

    @pytest.mark.ai
    def test_format_value__float(self) -> None:
        assert MCPMessageLogger._format_value(3.14) == "`3.14`"

    @pytest.mark.ai
    def test_format_value__bool_true(self) -> None:
        assert MCPMessageLogger._format_value(True) == "`true`"

    @pytest.mark.ai
    def test_format_value__bool_false(self) -> None:
        assert MCPMessageLogger._format_value(False) == "`false`"

    @pytest.mark.ai
    def test_format_value__none(self) -> None:
        assert MCPMessageLogger._format_value(None) == "_empty_"

    @pytest.mark.ai
    def test_format_value__truncates_long_string(self) -> None:
        result = MCPMessageLogger._format_value("a" * 300, max_length=10)
        assert result == "`aaaaaaaaaa...`"

    @pytest.mark.ai
    def test_format_value__empty_list(self) -> None:
        assert MCPMessageLogger._format_value([]) == "_empty list_"

    @pytest.mark.ai
    def test_format_value__empty_dict(self) -> None:
        assert MCPMessageLogger._format_value({}) == "_empty object_"


class TestExecuting:
    """Tests for the executing() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_creates_message_log_with_params__when_flag_enabled(
        self,
        mock_message_step_logger: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(mock_message_step_logger)

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=True)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=True)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.executing(mock_tool_call, {"query": "hello", "limit": 10})

        call_kwargs = mock_message_step_logger.create_or_update_message_log.call_args.kwargs
        progress = call_kwargs["progress_message"]
        assert "_Executing MCP tool_" in progress
        assert "**Search query**" in progress
        assert "`hello`" in progress
        assert "**Result limit**" in progress
        assert "`10`" in progress
        assert call_kwargs["status"] == MessageLogStatus.RUNNING

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_creates_message_log_without_params__when_flag_disabled(
        self,
        mock_message_step_logger: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(mock_message_step_logger)

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=False)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=True)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.executing(mock_tool_call, {"query": "hello"})

        call_kwargs = mock_message_step_logger.create_or_update_message_log.call_args.kwargs
        assert call_kwargs["progress_message"] == "_Executing MCP tool_"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_notifies_progress_reporter__when_old_ui_flag_disabled(
        self,
        mock_message_step_logger: Mock,
        mock_tool_progress_reporter: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(
            mock_message_step_logger,
            tool_progress_reporter=mock_tool_progress_reporter,
        )

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=False)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=False)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.executing(mock_tool_call, {"query": "test"})

        mock_tool_progress_reporter.notify_from_tool_call.assert_called_once()
        call_kwargs = mock_tool_progress_reporter.notify_from_tool_call.call_args.kwargs
        assert call_kwargs["state"] == ProgressState.RUNNING
        assert "Executing MCP tool" in call_kwargs["message"]
        assert "**Test Tool**" == call_kwargs["name"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_skips_progress_reporter__when_old_ui_flag_enabled(
        self,
        mock_message_step_logger: Mock,
        mock_tool_progress_reporter: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(
            mock_message_step_logger,
            tool_progress_reporter=mock_tool_progress_reporter,
        )

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=False)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=True)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.executing(mock_tool_call, {"query": "test"})

        mock_tool_progress_reporter.notify_from_tool_call.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_skips_progress_reporter__when_reporter_is_none(
        self,
        mock_message_step_logger: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(mock_message_step_logger, tool_progress_reporter=None)

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=False)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=False)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.executing(mock_tool_call, {"query": "test"})

        mock_message_step_logger.create_or_update_message_log.assert_called_once()


class TestCompleted:
    """Tests for the completed() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_updates_status_to_completed(
        self,
        mock_message_step_logger: Mock,
        mock_tool_progress_reporter: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(
            mock_message_step_logger,
            tool_progress_reporter=mock_tool_progress_reporter,
        )

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=False)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=False)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.completed(mock_tool_call, {"query": "test"})

        call_kwargs = mock_message_step_logger.create_or_update_message_log.call_args.kwargs
        assert call_kwargs["status"] == MessageLogStatus.COMPLETED
        assert "_Completed MCP tool_" in call_kwargs["progress_message"]

        reporter_kwargs = mock_tool_progress_reporter.notify_from_tool_call.call_args.kwargs
        assert reporter_kwargs["state"] == ProgressState.FINISHED
        assert "completed" in reporter_kwargs["message"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_completed_includes_params__when_flag_enabled(
        self,
        mock_message_step_logger: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(mock_message_step_logger)

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=True)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=True)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.completed(mock_tool_call, {"query": "hello"})

        call_kwargs = mock_message_step_logger.create_or_update_message_log.call_args.kwargs
        progress = call_kwargs["progress_message"]
        assert "_Completed MCP tool_" in progress
        assert "**Search query**" in progress


class TestFailed:
    """Tests for the failed() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_updates_status_to_failed(
        self,
        mock_message_step_logger: Mock,
        mock_tool_progress_reporter: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(
            mock_message_step_logger,
            tool_progress_reporter=mock_tool_progress_reporter,
        )

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=False)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=False)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.failed(mock_tool_call, "Something broke", {"query": "test"})

        call_kwargs = mock_message_step_logger.create_or_update_message_log.call_args.kwargs
        assert call_kwargs["status"] == MessageLogStatus.FAILED
        assert "_Failed executing MCP tool_" in call_kwargs["progress_message"]

        reporter_kwargs = mock_tool_progress_reporter.notify_from_tool_call.call_args.kwargs
        assert reporter_kwargs["state"] == ProgressState.FAILED
        assert "Something broke" in reporter_kwargs["message"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_failed_handles_none_arguments(
        self,
        mock_message_step_logger: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(mock_message_step_logger)

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=True)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=True)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.failed(mock_tool_call, "Error", None)

        call_kwargs = mock_message_step_logger.create_or_update_message_log.call_args.kwargs
        assert call_kwargs["progress_message"] == "_Failed executing MCP tool_"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_failed_includes_params__when_flag_enabled(
        self,
        mock_message_step_logger: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        logger = _make_logger(mock_message_step_logger)

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=True)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=True)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.failed(mock_tool_call, "Error", {"query": "test"})

        call_kwargs = mock_message_step_logger.create_or_update_message_log.call_args.kwargs
        progress = call_kwargs["progress_message"]
        assert "_Failed executing MCP tool_" in progress
        assert "**Search query**" in progress


class TestMessageLogChaining:
    """Tests that message log updates are chained (create then update)."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_second_call_passes_previous_message_log(
        self,
        mock_message_step_logger: Mock,
        mock_tool_call: LanguageModelFunction,
    ) -> None:
        first_log = Mock(spec=MessageLog)
        mock_message_step_logger.create_or_update_message_log.return_value = first_log

        logger = _make_logger(mock_message_step_logger)

        mock_flags = Mock()
        mock_flags.enable_mcp_tool_params_display.is_enabled = Mock(return_value=False)
        mock_flags.enable_new_answers_ui_un_14411.is_enabled = Mock(return_value=True)

        with patch(FEATURE_FLAGS_PATH, mock_flags):
            await logger.executing(mock_tool_call, {"query": "test"})
            await logger.completed(mock_tool_call, {"query": "test"})

        calls = mock_message_step_logger.create_or_update_message_log.call_args_list
        assert calls[0].kwargs["active_message_log"] is None
        assert calls[1].kwargs["active_message_log"] is first_log
