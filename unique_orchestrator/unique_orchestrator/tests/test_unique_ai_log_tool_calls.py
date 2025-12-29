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
        mock_loop_iteration_runner = MagicMock()

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
            loop_iteration_runner=mock_loop_iteration_runner,
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
            text="**Triggered Tool Calls:**\n - Search Tool", references=[]
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
            text="**Triggered Tool Calls:**\n - Search Tool\n - Web Search",
            references=[],
        )

    @pytest.mark.ai
    def test_log_tool_calls__uses_tool_name__when_tool_not_in_available_tools(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls does not create a message log entry when the tool is not found in available_tools.
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
        # Tool call not in available_tools should not create a log entry
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 0
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
            text="**Triggered Tool Calls:**\n - search_tool", references=[]
        )

    @pytest.mark.ai
    def test_log_tool_calls__handles_empty_list__without_error(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls handles an empty tool_calls list without raising errors and does not create a log entry.

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
        # Empty tool_calls list should not create a log entry
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 0
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

    @pytest.mark.ai
    def test_log_tool_calls__excludes_deep_research_from_message_log__but_adds_to_history(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls excludes "DeepResearch" from the message log entry but still adds it to history.

        Why this matters: DeepResearch tool calls should be tracked in history for completeness but hidden from the user-facing message steps to avoid clutter or confusion.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with "DeepResearch" and other tools, and provide tool calls including "DeepResearch".
        """
        # Arrange
        mock_tool_1 = MagicMock(spec=["name", "display_name"])
        mock_tool_1.name = "DeepResearch"
        mock_tool_1.display_name.return_value = "Deep Research"

        mock_tool_2 = MagicMock(spec=["name", "display_name"])
        mock_tool_2.name = "search_tool"
        mock_tool_2.display_name.return_value = "Search Tool"

        mock_unique_ai._tool_manager.available_tools = [mock_tool_1, mock_tool_2]

        mock_tool_call_1 = MagicMock(spec=["name"])
        mock_tool_call_1.name = "DeepResearch"

        mock_tool_call_2 = MagicMock(spec=["name"])
        mock_tool_call_2.name = "search_tool"

        tool_calls = [mock_tool_call_1, mock_tool_call_2]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        # Both tool calls should be added to history
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 2
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_1)
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_2)

        # But only the non-DeepResearch tool should appear in the message log
        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n - Search Tool", references=[]
        )

    @pytest.mark.ai
    def test_log_tool_calls__excludes_only_deep_research_when_present__with_multiple_tools(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls only excludes "DeepResearch" and logs all other tools when multiple tools are called.

        Why this matters: The exclusion logic should be precise, affecting only "DeepResearch" while allowing all other tools to be logged normally.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with multiple tools including "DeepResearch", and provide multiple tool calls.
        """
        # Arrange
        mock_tool_1 = MagicMock(spec=["name", "display_name"])
        mock_tool_1.name = "DeepResearch"
        mock_tool_1.display_name.return_value = "Deep Research"

        mock_tool_2 = MagicMock(spec=["name", "display_name"])
        mock_tool_2.name = "search_tool"
        mock_tool_2.display_name.return_value = "Search Tool"

        mock_tool_3 = MagicMock(spec=["name", "display_name"])
        mock_tool_3.name = "web_search"
        mock_tool_3.display_name.return_value = "Web Search"

        mock_unique_ai._tool_manager.available_tools = [
            mock_tool_1,
            mock_tool_2,
            mock_tool_3,
        ]

        mock_tool_call_1 = MagicMock(spec=["name"])
        mock_tool_call_1.name = "search_tool"

        mock_tool_call_2 = MagicMock(spec=["name"])
        mock_tool_call_2.name = "DeepResearch"

        mock_tool_call_3 = MagicMock(spec=["name"])
        mock_tool_call_3.name = "web_search"

        tool_calls = [mock_tool_call_1, mock_tool_call_2, mock_tool_call_3]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        # All tool calls should be added to history
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 3
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_1)
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_2)
        mock_unique_ai._history_manager.add_tool_call.assert_any_call(mock_tool_call_3)

        # But only the non-DeepResearch tools should appear in the message log
        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n - Search Tool\n - Web Search",
            references=[],
        )

    @pytest.mark.ai
    def test_log_tool_calls__creates_no_log_entry__when_only_deep_research_called(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls does not create a message log entry when only "DeepResearch" is called.

        Why this matters: When only excluded tools are called, no message log entry should be created since there's nothing to display to the user.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with "DeepResearch", and provide only a DeepResearch tool call.
        """
        # Arrange
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "DeepResearch"
        mock_tool.display_name.return_value = "Deep Research"

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        mock_tool_call = MagicMock(spec=["name"])
        mock_tool_call.name = "DeepResearch"

        tool_calls = [mock_tool_call]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        # DeepResearch should be added to history
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 1
        mock_unique_ai._history_manager.add_tool_call.assert_called_once_with(
            mock_tool_call
        )

        # But no message log entry should be created since tool_string is empty
        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 0
        )

    @pytest.mark.ai
    def test_log_tool_calls__displays_count__when_same_tool_called_multiple_times(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls displays a count indicator when the same tool is called multiple times.

        Why this matters: Users should see how many times each tool was invoked to understand the execution pattern. Multiple calls to the same tool should be aggregated with a count suffix.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with one available tool, and provide multiple calls to the same tool.
        """
        # Arrange
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "search_tool"
        mock_tool.display_name.return_value = "Search Tool"

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        mock_tool_call_1 = MagicMock(spec=["name"])
        mock_tool_call_1.name = "search_tool"

        mock_tool_call_2 = MagicMock(spec=["name"])
        mock_tool_call_2.name = "search_tool"

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
        # Should display "(2x)" for the tool called twice
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n - Search Tool (2x)", references=[]
        )

    @pytest.mark.ai
    def test_log_tool_calls__displays_count__when_same_tool_called_three_times(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls correctly displays count for tools called three or more times.

        Why this matters: The counting logic should work for any number of duplicate calls, not just two.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with one available tool, and provide three calls to the same tool.
        """
        # Arrange
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "search_tool"
        mock_tool.display_name.return_value = "Search Tool"

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        mock_tool_call_1 = MagicMock(spec=["name"])
        mock_tool_call_1.name = "search_tool"

        mock_tool_call_2 = MagicMock(spec=["name"])
        mock_tool_call_2.name = "search_tool"

        mock_tool_call_3 = MagicMock(spec=["name"])
        mock_tool_call_3.name = "search_tool"

        tool_calls = [mock_tool_call_1, mock_tool_call_2, mock_tool_call_3]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 3

        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        # Should display "(3x)" for the tool called three times
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n - Search Tool (3x)", references=[]
        )

    @pytest.mark.ai
    def test_log_tool_calls__displays_mixed_counts__with_some_tools_called_once_and_others_multiple_times(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls correctly handles a mix of tools called once and tools called multiple times.

        Why this matters: Real-world scenarios often involve calling different tools different numbers of times. The log should accurately reflect this with counts only shown for tools called more than once.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with multiple available tools, and provide a mix of single and multiple calls.
        """
        # Arrange
        mock_tool_1 = MagicMock(spec=["name", "display_name"])
        mock_tool_1.name = "search_tool"
        mock_tool_1.display_name.return_value = "Search Tool"

        mock_tool_2 = MagicMock(spec=["name", "display_name"])
        mock_tool_2.name = "web_search"
        mock_tool_2.display_name.return_value = "Web Search"

        mock_tool_3 = MagicMock(spec=["name", "display_name"])
        mock_tool_3.name = "file_reader"
        mock_tool_3.display_name.return_value = "File Reader"

        mock_unique_ai._tool_manager.available_tools = [
            mock_tool_1,
            mock_tool_2,
            mock_tool_3,
        ]

        mock_tool_call_1 = MagicMock(spec=["name"])
        mock_tool_call_1.name = "search_tool"

        mock_tool_call_2 = MagicMock(spec=["name"])
        mock_tool_call_2.name = "web_search"

        mock_tool_call_3 = MagicMock(spec=["name"])
        mock_tool_call_3.name = "search_tool"

        mock_tool_call_4 = MagicMock(spec=["name"])
        mock_tool_call_4.name = "file_reader"

        mock_tool_call_5 = MagicMock(spec=["name"])
        mock_tool_call_5.name = "search_tool"

        tool_calls = [
            mock_tool_call_1,
            mock_tool_call_2,
            mock_tool_call_3,
            mock_tool_call_4,
            mock_tool_call_5,
        ]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 5

        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        # Should display:
        # - "Search Tool (3x)" for search_tool (called 3 times)
        # - "Web Search" for web_search (called once, no count)
        # - "File Reader" for file_reader (called once, no count)
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n - Search Tool (3x)\n - Web Search\n - File Reader",
            references=[],
        )

    @pytest.mark.ai
    def test_log_tool_calls__excludes_deep_research_from_count__when_called_multiple_times(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that _log_tool_calls excludes "DeepResearch" from message log even when it's called multiple times, but still adds all instances to history.

        Why this matters: The exclusion of DeepResearch should work consistently regardless of how many times it's called.

        Setup summary: Create a UniqueAI instance with mocked dependencies, set up a tool manager with "DeepResearch" and other tools, and provide multiple DeepResearch calls along with other tool calls.
        """
        # Arrange
        mock_tool_1 = MagicMock(spec=["name", "display_name"])
        mock_tool_1.name = "DeepResearch"
        mock_tool_1.display_name.return_value = "Deep Research"

        mock_tool_2 = MagicMock(spec=["name", "display_name"])
        mock_tool_2.name = "search_tool"
        mock_tool_2.display_name.return_value = "Search Tool"

        mock_unique_ai._tool_manager.available_tools = [mock_tool_1, mock_tool_2]

        mock_tool_call_1 = MagicMock(spec=["name"])
        mock_tool_call_1.name = "DeepResearch"

        mock_tool_call_2 = MagicMock(spec=["name"])
        mock_tool_call_2.name = "search_tool"

        mock_tool_call_3 = MagicMock(spec=["name"])
        mock_tool_call_3.name = "DeepResearch"

        mock_tool_call_4 = MagicMock(spec=["name"])
        mock_tool_call_4.name = "search_tool"

        tool_calls = [
            mock_tool_call_1,
            mock_tool_call_2,
            mock_tool_call_3,
            mock_tool_call_4,
        ]

        # Act
        mock_unique_ai._log_tool_calls(tool_calls)

        # Assert
        # All tool calls should be added to history
        assert isinstance(mock_unique_ai._history_manager.add_tool_call.call_count, int)
        assert mock_unique_ai._history_manager.add_tool_call.call_count == 4

        # But only the non-DeepResearch tool should appear in the message log, with correct count
        assert isinstance(
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count,
            int,
        )
        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 1
        )
        # DeepResearch should be excluded, only Search Tool (2x) should appear
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n - Search Tool (2x)", references=[]
        )
