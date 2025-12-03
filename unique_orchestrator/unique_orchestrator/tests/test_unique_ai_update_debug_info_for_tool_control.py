from unittest.mock import AsyncMock, MagicMock

import pytest


class TestUpdateDebugInfoForToolControl:
    """Test suite for UniqueAI._update_debug_info_if_tool_took_control method"""

    @pytest.fixture
    def mock_unique_ai(self):
        """Create a minimal UniqueAI instance with mocked dependencies"""
        # Lazy import to avoid heavy dependencies at module import time
        from unique_orchestrator.unique_ai import UniqueAI

        mock_logger = MagicMock()

        # Create minimal event structure
        dummy_event = MagicMock()
        dummy_event.payload.assistant_message.id = "assist_1"
        dummy_event.payload.user_message.text = "query"
        dummy_event.payload.assistant_id = "assistant_123"
        dummy_event.payload.name = "TestAssistant"
        dummy_event.payload.user_metadata = {"key": "value"}
        dummy_event.payload.tool_parameters = {"param": "value"}

        # Create minimal config structure
        mock_config = MagicMock()
        mock_config.agent.prompt_config.user_metadata = []

        # Create minimal required dependencies
        mock_chat_service = MagicMock()
        mock_chat_service.update_debug_info_async = AsyncMock()
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
    @pytest.mark.asyncio
    async def test_does_not_update_debug_info_when_tool_did_not_take_control(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that _update_debug_info_if_tool_took_control does nothing when
        _tool_took_control is False.

        Why this matters: Debug info should only be updated when a tool takes control
        of the conversation. When no tool takes control, no update should occur.

        Setup summary: Create a UniqueAI instance with _tool_took_control set to False.
        """
        # Arrange
        mock_unique_ai._tool_took_control = False
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "SearchTool"}]
        }

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert
        mock_unique_ai._chat_service.update_debug_info_async.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_does_not_update_debug_info_if_tool_took_control_and_deep_research_is_in_tool_names(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that _update_debug_info_if_tool_took_control does nothing when
        DeepResearch is among the called tools.

        Why this matters: DeepResearch handles debug info directly since it calls
        the orchestrator multiple times, so we should not update debug info here.

        Setup summary: Create a UniqueAI instance with _tool_took_control set to True
        and DeepResearch in the tools list.
        """
        # Arrange
        mock_unique_ai._tool_took_control = True
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "DeepResearch"}, {"name": "SearchTool"}]
        }

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert
        mock_unique_ai._chat_service.update_debug_info_async.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_does_not_update_debug_info_if_tool_took_control_and_only_deep_research_is_called(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that _update_debug_info_if_tool_took_control does nothing when
        only DeepResearch is the called tool.

        Why this matters: Even when DeepResearch is the only tool, we should still
        skip the debug info update because DeepResearch manages its own debug info.

        Setup summary: Create a UniqueAI instance with _tool_took_control set to True
        and only DeepResearch in the tools list.
        """
        # Arrange
        mock_unique_ai._tool_took_control = True
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "DeepResearch"}]
        }

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert
        mock_unique_ai._chat_service.update_debug_info_async.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_updates_debug_info_when_tool_took_control_without_deep_research(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that _update_debug_info_if_tool_took_control updates debug info
        when a tool takes control and DeepResearch is not among the tools.

        Why this matters: When a non-DeepResearch tool takes control, we need to
        update the debug info with the relevant conversation context.

        Setup summary: Create a UniqueAI instance with _tool_took_control set to True
        and no DeepResearch in the tools list.
        """
        # Arrange
        mock_unique_ai._tool_took_control = True
        debug_info = {"tools": [{"name": "SearchTool"}, {"name": "WebSearch"}]}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert
        expected_debug_info_event = {
            "tools": debug_info,
            "assistant": {
                "id": "assistant_123",
                "name": "TestAssistant",
            },
            "chosenModule": "TestAssistant",
            "userMetadata": {"key": "value"},
            "toolParameters": {"param": "value"},
        }
        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once_with(
            debug_info=expected_debug_info_event
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_updates_debug_info_with_single_tool(self, mock_unique_ai) -> None:
        """
        Purpose: Verify that _update_debug_info_if_tool_took_control correctly formats
        the debug info event with a single tool.

        Why this matters: The debug info event structure must be correct for the
        frontend to properly display the tool execution context.

        Setup summary: Create a UniqueAI instance with _tool_took_control set to True
        and a single non-DeepResearch tool.
        """
        # Arrange
        mock_unique_ai._tool_took_control = True
        debug_info = {"tools": [{"name": "SWOT"}]}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert
        expected_debug_info_event = {
            "tools": debug_info,
            "assistant": {
                "id": "assistant_123",
                "name": "TestAssistant",
            },
            "chosenModule": "TestAssistant",
            "userMetadata": {"key": "value"},
            "toolParameters": {"param": "value"},
        }
        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once_with(
            debug_info=expected_debug_info_event
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_updates_debug_info_with_none_user_metadata(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that _update_debug_info_if_tool_took_control handles None
        user_metadata correctly.

        Why this matters: User metadata can be None, and the function should handle
        this gracefully without errors.

        Setup summary: Create a UniqueAI instance with _tool_took_control set to True,
        no DeepResearch in tools, and None user_metadata.
        """
        # Arrange
        mock_unique_ai._tool_took_control = True
        mock_unique_ai._event.payload.user_metadata = None
        debug_info = {"tools": [{"name": "SearchTool"}]}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert
        expected_debug_info_event = {
            "tools": debug_info,
            "assistant": {
                "id": "assistant_123",
                "name": "TestAssistant",
            },
            "chosenModule": "TestAssistant",
            "userMetadata": None,
            "toolParameters": {"param": "value"},
        }
        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once_with(
            debug_info=expected_debug_info_event
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_updates_debug_info_with_none_tool_parameters(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that _update_debug_info_if_tool_took_control handles None
        tool_parameters correctly.

        Why this matters: Tool parameters can be None, and the function should handle
        this gracefully without errors.

        Setup summary: Create a UniqueAI instance with _tool_took_control set to True,
        no DeepResearch in tools, and None tool_parameters.
        """
        # Arrange
        mock_unique_ai._tool_took_control = True
        mock_unique_ai._event.payload.tool_parameters = None
        debug_info = {"tools": [{"name": "SearchTool"}]}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert
        expected_debug_info_event = {
            "tools": debug_info,
            "assistant": {
                "id": "assistant_123",
                "name": "TestAssistant",
            },
            "chosenModule": "TestAssistant",
            "userMetadata": {"key": "value"},
            "toolParameters": None,
        }
        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once_with(
            debug_info=expected_debug_info_event
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_updates_debug_info_with_empty_tools_list(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that _update_debug_info_if_tool_took_control updates debug info
        when the tools list is empty.

        Why this matters: Even with an empty tools list, if _tool_took_control is True,
        the debug info should still be updated (edge case).

        Setup summary: Create a UniqueAI instance with _tool_took_control set to True
        and an empty tools list.
        """
        # Arrange
        mock_unique_ai._tool_took_control = True
        debug_info = {"tools": []}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert
        expected_debug_info_event = {
            "tools": debug_info,
            "assistant": {
                "id": "assistant_123",
                "name": "TestAssistant",
            },
            "chosenModule": "TestAssistant",
            "userMetadata": {"key": "value"},
            "toolParameters": {"param": "value"},
        }
        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once_with(
            debug_info=expected_debug_info_event
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_deep_research_check_is_case_sensitive(self, mock_unique_ai) -> None:
        """
        Purpose: Verify that the DeepResearch check is case-sensitive.

        Why this matters: The check for "DeepResearch" should be exact match.
        Tools with different casing (e.g., "deepresearch", "DEEPRESEARCH") should
        not trigger the early return.

        Setup summary: Create a UniqueAI instance with _tool_took_control set to True
        and tools with similar but not exact "DeepResearch" names.
        """
        # Arrange
        mock_unique_ai._tool_took_control = True
        debug_info = {"tools": [{"name": "deepresearch"}, {"name": "DEEPRESEARCH"}]}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        # Act
        await mock_unique_ai._update_debug_info_if_tool_took_control()

        # Assert - should update because "DeepResearch" exact match is not found
        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once()

