"""Tests for main SWOT service/tool."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.language_model.schemas import LanguageModelToolDescription

from unique_swot.config import SwotAnalysisToolConfig
from unique_swot.service import SwotAnalysisTool
from unique_swot.services.schemas import SWOTPlan


class TestSwotTool:
    """Test cases for SwotTool class."""

    @pytest.fixture
    def swot_config(self):
        """Create a SwotConfig for testing."""
        return SwotAnalysisToolConfig(cache_scope_id="test_scope")

    @pytest.fixture
    def mock_event(self):
        """Create a mock event."""
        event = Mock()
        event.company_id = "test_company"
        event.user_id = "test_user"
        event.payload.chat_id = "test_chat"
        event.payload.assistant_message = Mock(id="test_message")
        return event

    def test_swot_tool_name(self):
        """Test SwotTool name attribute."""
        assert SwotAnalysisTool.name == "SWOT"

    def test_swot_tool_initialization(self, swot_config, mock_event):
        """Test SwotTool initialization."""
        with (
            patch("unique_toolkit.agentic.tools.tool.ChatService", return_value=Mock()),
            patch(
                "unique_toolkit.agentic.tools.tool.LanguageModelService",
                return_value=Mock(),
            ),
            patch(
                "unique_swot.service.KnowledgeBaseService.from_event",
                return_value=Mock(),
            ),
            patch("unique_swot.service.ShortTermMemoryService", return_value=Mock()),
        ):
            tool = SwotAnalysisTool(configuration=swot_config, event=mock_event)

            assert tool.config == swot_config
            assert tool._notifier is not None

    def test_swot_tool_tool_description(self, swot_config, mock_event):
        """Test tool_description method."""
        with (
            patch("unique_toolkit.agentic.tools.tool.ChatService", return_value=Mock()),
            patch(
                "unique_toolkit.agentic.tools.tool.LanguageModelService",
                return_value=Mock(),
            ),
            patch(
                "unique_swot.service.KnowledgeBaseService.from_event",
                return_value=Mock(),
            ),
            patch("unique_swot.service.ShortTermMemoryService", return_value=Mock()),
        ):
            tool = SwotAnalysisTool(configuration=swot_config, event=mock_event)

            description = tool.tool_description()

            assert isinstance(description, LanguageModelToolDescription)
            assert description.name == "SWOT"
            assert description.parameters == SWOTPlan

    def test_swot_tool_description_methods(self, swot_config, mock_event):
        """Test various description methods."""
        with (
            patch("unique_toolkit.agentic.tools.tool.ChatService", return_value=Mock()),
            patch(
                "unique_toolkit.agentic.tools.tool.LanguageModelService",
                return_value=Mock(),
            ),
            patch(
                "unique_swot.service.KnowledgeBaseService.from_event",
                return_value=Mock(),
            ),
            patch("unique_swot.service.ShortTermMemoryService", return_value=Mock()),
        ):
            tool = SwotAnalysisTool(configuration=swot_config, event=mock_event)

            assert isinstance(tool.tool_description_for_system_prompt(), str)
            assert isinstance(tool.tool_format_information_for_system_prompt(), str)
            assert isinstance(tool.tool_description_for_user_prompt(), str)
            assert isinstance(tool.tool_format_information_for_user_prompt(), str)
            assert isinstance(tool.tool_format_reminder_for_user_prompt(), str)

    def test_swot_tool_takes_control(self, swot_config, mock_event):
        """Test that SwotTool takes control of conversation."""
        with (
            patch("unique_toolkit.agentic.tools.tool.ChatService", return_value=Mock()),
            patch(
                "unique_toolkit.agentic.tools.tool.LanguageModelService",
                return_value=Mock(),
            ),
            patch(
                "unique_swot.service.KnowledgeBaseService.from_event",
                return_value=Mock(),
            ),
            patch("unique_swot.service.ShortTermMemoryService", return_value=Mock()),
        ):
            tool = SwotAnalysisTool(configuration=swot_config, event=mock_event)

            assert tool.takes_control() is True

    @pytest.mark.asyncio
    async def test_swot_tool_run_basic(self, swot_config, mock_event, sample_swot_plan):
        """Test running SwotTool with a basic plan."""
        with (
            patch("unique_toolkit.agentic.tools.tool.ChatService", return_value=Mock()),
            patch(
                "unique_toolkit.agentic.tools.tool.LanguageModelService",
                return_value=Mock(),
            ),
            patch(
                "unique_swot.service.KnowledgeBaseService.from_event",
                return_value=Mock(),
            ),
            patch("unique_swot.service.ShortTermMemoryService", return_value=Mock()),
            patch("unique_swot.service.SWOTExecutionManager") as mock_executor_class,
        ):
            tool = SwotAnalysisTool(configuration=swot_config, event=mock_event)

            # Mock the executor
            mock_executor = Mock()
            mock_result = Mock()
            mock_result.model_dump.return_value = {
                "objective": "Test",
                "strengths": {"result": "Strong"},
                "weaknesses": {"result": "Weak"},
                "opportunities": {"result": "Opportunities"},
                "threats": {"result": "Threats"},
            }
            mock_executor.run = AsyncMock(return_value=mock_result)
            mock_executor_class.return_value = mock_executor

            # Mock the source collection
            tool._source_collection_manager.collect_sources = Mock(return_value=[])

            # Mock citation manager
            tool._citation_manager.get_references = Mock(return_value=[])
            tool._citation_manager.get_referenced_content_chunks = Mock(return_value=[])

            # Create a mock tool call
            tool_call = Mock()
            tool_call.id = "call_123"
            tool_call.arguments = sample_swot_plan.model_dump()

            result = await tool.run(tool_call)

            assert result is not None
            assert result.name == "SWOT"
            assert result.id == "call_123"

    def test_swot_tool_evaluation_checks(self, swot_config, mock_event):
        """Test evaluation check methods."""
        with (
            patch("unique_toolkit.agentic.tools.tool.ChatService", return_value=Mock()),
            patch(
                "unique_toolkit.agentic.tools.tool.LanguageModelService",
                return_value=Mock(),
            ),
            patch(
                "unique_swot.service.KnowledgeBaseService.from_event",
                return_value=Mock(),
            ),
            patch("unique_swot.service.ShortTermMemoryService", return_value=Mock()),
        ):
            tool = SwotAnalysisTool(configuration=swot_config, event=mock_event)

            mock_response = Mock()
            checks = tool.get_evaluation_checks_based_on_tool_response(mock_response)

            assert isinstance(checks, list)
            assert len(checks) == 0

            check_list = tool.evaluation_check_list()
            assert isinstance(check_list, list)
            assert len(check_list) == 0

    def test_swot_tool_get_tool_call_result_for_loop_history(
        self, swot_config, mock_event
    ):
        """Test get_tool_call_result_for_loop_history method."""
        with (
            patch("unique_toolkit.agentic.tools.tool.ChatService", return_value=Mock()),
            patch(
                "unique_toolkit.agentic.tools.tool.LanguageModelService",
                return_value=Mock(),
            ),
            patch(
                "unique_swot.service.KnowledgeBaseService.from_event",
                return_value=Mock(),
            ),
            patch("unique_swot.service.ShortTermMemoryService", return_value=Mock()),
        ):
            tool = SwotAnalysisTool(configuration=swot_config, event=mock_event)

            mock_response = Mock()
            mock_response.content = "Test content"
            mock_handler = Mock()

            result = tool.get_tool_call_result_for_loop_history(
                mock_response, mock_handler
            )

            assert result.content == "Test content"
