from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


class TestLogToolCalls:
    """Test suite for UniqueAI._log_tool_calls method"""

    @pytest.fixture
    def mock_unique_ai(self, monkeypatch):
        """Create a minimal UniqueAI instance with mocked dependencies"""
        # Mock MessageStepLogger before importing UniqueAI to avoid import errors
        mock_message_step_logger_class = MagicMock()
        mock_service_module = MagicMock()
        mock_service_module.MessageStepLogger = mock_message_step_logger_class

        # Use monkeypatch to set the module in sys.modules before import
        import sys

        monkeypatch.setitem(
            sys.modules,
            "unique_toolkit.agentic.message_log_manager.service",
            mock_service_module,
        )

        # Lazy import to avoid heavy dependencies at module import time
        from unique_orchestrator.unique_ai import UniqueAI

        mock_logger = MagicMock()

        # Create minimal event structure
        dummy_event = MagicMock()
        dummy_event.payload.assistant_message.id = "assist_1"
        dummy_event.payload.user_message.text = "query"

        # Create minimal config structure
        mock_config = MagicMock()
        mock_config.agent.prompt_config.user_metadata = []

        # Create minimal required dependencies
        mock_chat_service = MagicMock()
        mock_content_service = MagicMock()
        mock_debug_info_manager = MagicMock()
        mock_reference_manager = MagicMock()
        mock_thinking_manager = MagicMock()
        mock_tool_manager = MagicMock()
        mock_history_manager = MagicMock()
        mock_evaluation_manager = MagicMock()
        mock_postprocessor_manager = MagicMock()
        mock_streaming_handler = MagicMock()
        mock_message_step_logger = MagicMock()

        # Instantiate UniqueAI
        ua = UniqueAI(
            logger=mock_logger,
            event=dummy_event,
            config=mock_config,
            chat_service=mock_chat_service,
            content_service=mock_content_service,
            debug_info_manager=mock_debug_info_manager,
            streaming_handler=mock_streaming_handler,
            reference_manager=mock_reference_manager,
            thinking_manager=mock_thinking_manager,
            tool_manager=mock_tool_manager,
            history_manager=mock_history_manager,
            evaluation_manager=mock_evaluation_manager,
            postprocessor_manager=mock_postprocessor_manager,
            message_step_logger=mock_message_step_logger,
            mcp_servers=[],
        )

        return ua

    @pytest.mark.ai
    def test_log_tool_calls__creates_log_entry__with_single_tool_call(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls creates a message log entry with the correct format when a single tool call is provided.

        Why this matters: The logging of tool calls is critical for user visibility and debugging. The function must correctly format and log tool call information.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with one available tool, and provide a single tool call.
        """
        # Arrange
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "search_tool"
        mock_tool.display_name.return_value = "Search Tool"

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        mock_tool_call = MagicMock(spec=["name"])
        mock_tool_call.name = "search_tool"

        tool_calls = [mock_tool_call]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 1
        mock_unique_ai._history_manager.add_tool_call.assert_called_once_with(
            mock_tool_call
        )

        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n \n• Search Tool", references=[]
        )

    @pytest.mark.ai
    def test_log_tool_calls__creates_log_entry__with_multiple_tool_calls(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls correctly formats and logs multiple tool calls in a single log entry.

        Why this matters: Users may trigger multiple tools simultaneously, and all should be logged in a readable format.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with multiple available tools, and provide multiple tool calls.
        """
        # Arrange
        mock_tool_1 = MagicMock(spec=["name", "display_name"])
        mock_tool_1.name = "search_tool"
        mock_tool_1.display_name.return_value = "Search Tool"

        mock_tool_2 = MagicMock(spec=["name", "display_name"])
        mock_tool_2.name = "web_search"
        mock_tool_2.display_name.return_value = "Web Search"

        mock_unique_ai._tool_manager.available_tools = [mock_tool_1, mock_tool_2]

        mock_tool_call_1 = MagicMock(spec=["name"])
        mock_tool_call_1.name = "search_tool"

        mock_tool_call_2 = MagicMock(spec=["name"])
        mock_tool_call_2.name = "web_search"

        tool_calls = [mock_tool_call_1, mock_tool_call_2]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 2
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_1)
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_2)

        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n \n• Search Tool\n• Web Search",
            references=[],
        )

    @pytest.mark.ai
    def test_log_tool_calls__uses_tool_name__when_tool_not_in_available_tools(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls uses the tool call's name directly when the tool is not found in available_tools.

        Why this matters: The function should gracefully handle tool calls for tools that are not in the available_tools list, ensuring logging continues to work.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with no matching tools, and provide a tool call with a name not in available_tools.
        """
        # Arrange
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "other_tool"
        mock_tool.display_name.return_value = "Other Tool"

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        mock_tool_call = MagicMock(spec=["name"])
        mock_tool_call.name = "unknown_tool"

        tool_calls = [mock_tool_call]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 1
        mock_unique_ai._history_manager.add_tool_call.assert_called_once_with(
            mock_tool_call
        )

        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        # Tool call not in available_tools should not appear in the tool_string
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n ", references=[]
        )

    @pytest.mark.ai
    def test_log_tool_calls__uses_tool_name__when_display_name_is_falsy(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls falls back to the tool call's name when display_name returns a falsy value.

        Why this matters: The function must handle edge cases where display_name might return None or empty string, ensuring the log entry always contains meaningful information.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with a tool that returns a falsy display_name, and provide a matching tool call.
        """
        # Arrange
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "search_tool"
        mock_tool.display_name.return_value = None

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        mock_tool_call = MagicMock(spec=["name"])
        mock_tool_call.name = "search_tool"

        tool_calls = [mock_tool_call]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 1
        mock_unique_ai._history_manager.add_tool_call.assert_called_once_with(
            mock_tool_call
        )

        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        # When display_name is falsy, should use tool_call.name
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n \n• search_tool", references=[]
        )

    @pytest.mark.ai
    def test_log_tool_calls__handles_empty_list__without_error(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls handles an empty tool_calls list without raising errors.

        Why this matters: The function should be resilient to edge cases like empty input, ensuring the system continues to function even when no tool calls are present.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with available tools, and provide an empty tool_calls list.
        """
        # Arrange
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "search_tool"
        mock_tool.display_name.return_value = "Search Tool"

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        tool_calls: list = []

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 0

        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n ", references=[]
        )

    @pytest.mark.ai
    def test_log_tool_calls__adds_all_tool_calls_to_history__regardless_of_availability(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls adds all tool calls to history, even if they are not in the available_tools list.

        Why this matters: History tracking should be complete and independent of whether tools are available for display name lookup.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with some available tools, and provide tool calls including both available and unavailable tools.
        """
        # Arrange
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "search_tool"
        mock_tool.display_name.return_value = "Search Tool"

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        mock_tool_call_1 = MagicMock(spec=["name"])
        mock_tool_call_1.name = "search_tool"

        mock_tool_call_2 = MagicMock(spec=["name"])
        mock_tool_call_2.name = "unknown_tool"

        tool_calls = [mock_tool_call_1, mock_tool_call_2]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 2
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_1)
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_2)

        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
