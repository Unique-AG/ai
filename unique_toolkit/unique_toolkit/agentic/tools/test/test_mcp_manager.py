import logging
from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from tests.test_obj_factory import get_event_obj
from unique_toolkit.agentic.tools.a2a.manager import A2AManager
from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_manager import ToolManager, ToolManagerConfig
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import McpServer, McpTool
from unique_toolkit.chat.service import ChatService


class MockParameters(BaseModel):
    pass


class MockInternalSearchTool(Tool[BaseToolConfig]):
    """Mock internal search tool for testing"""

    name = "internal_search"

    def __init__(self, config, event, tool_progress_reporter=None):
        super().__init__(config, event, tool_progress_reporter)

    def tool_description(self):
        from unique_toolkit.language_model.schemas import LanguageModelToolDescription

        return LanguageModelToolDescription(
            name="internal_search",
            description="Internal search tool for testing",
            parameters=MockParameters,
        )

    def tool_description_for_system_prompt(self) -> str:
        return "Internal search tool for searching content"

    def tool_format_information_for_system_prompt(self) -> str:
        return "Use this tool to search for content"

    def get_tool_call_result_for_loop_history(self, tool_response):
        from unique_toolkit.language_model.schemas import LanguageModelMessage

        return LanguageModelMessage(role="tool", content="Mock search result")

    def evaluation_check_list(self):
        return []

    def get_evaluation_checks_based_on_tool_response(self, tool_response):
        return []

    def get_tool_prompts(self):
        from unique_toolkit.agentic.tools.schemas import ToolPrompts

        return ToolPrompts()

    async def run(self, tool_call):
        from unique_toolkit.agentic.tools.schemas import ToolCallResponse

        return ToolCallResponse(id=tool_call.id, name=tool_call.name, content_chunks=[])


class MockInternalSearchConfig(BaseToolConfig):
    """Mock configuration for internal search tool"""

    pass


class TestMCPManager:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.logger = logging.getLogger(__name__)

        # Register mock internal tool
        ToolFactory.register_tool(MockInternalSearchTool, MockInternalSearchConfig)

        self.event = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )

        # Set tool choices to include both internal and MCP tools
        self.event.payload.tool_choices = ["internal_search", "mcp_test_tool"]
        self.event.payload.disabled_tools = []

    @pytest.fixture
    def mock_chat_service(self):
        """Create mock chat service for tool progress reporter"""
        return Mock(spec=ChatService)

    @pytest.fixture
    def tool_progress_reporter(self, mock_chat_service):
        """Create tool progress reporter fixture"""
        return ToolProgressReporter(mock_chat_service)

    @pytest.fixture
    def mcp_tools(self):
        """Create mock MCP tools fixture"""
        mcp_tool = McpTool(
            id="mcp_test_tool_id",
            name="mcp_test_tool",
            description="Test MCP tool",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
            output_schema=None,
            annotations=None,
            title="Test MCP Tool",
            icon=None,
            system_prompt=None,
            user_prompt=None,
            is_connected=True,
        )
        return [mcp_tool]

    @pytest.fixture
    def mcp_servers(self, mcp_tools):
        """Create mock MCP servers fixture"""
        server = McpServer(
            id="test_server_id",
            name="test_server",
            description="Test MCP server",
            tools=mcp_tools,
            system_prompt="Test system prompt",
            user_prompt="Test user prompt",
            is_connected=True,
        )
        return [server]

    @pytest.fixture
    def internal_tools(self):
        """Create internal tools fixture"""
        internal_tool_config = ToolBuildConfig(
            name="internal_search",
            configuration=MockInternalSearchConfig(),
            display_name="Internal Search",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        )
        return [internal_tool_config]

    @pytest.fixture
    def mcp_manager(self, mcp_servers, tool_progress_reporter):
        """Create MCP manager fixture"""
        return MCPManager(
            mcp_servers=mcp_servers,
            event=self.event,
            tool_progress_reporter=tool_progress_reporter,
        )

    @pytest.fixture
    def a2a_manager(self, tool_progress_reporter):
        """Create MCP manager fixture"""
        return A2AManager(
            logger=self.logger,
            tool_progress_reporter=tool_progress_reporter,
        )

    @pytest.fixture
    def tool_manager_config(self, internal_tools):
        """Create tool manager configuration fixture"""
        return ToolManagerConfig(tools=internal_tools, max_tool_calls=10)

    @pytest.fixture
    def tool_manager(
        self, tool_manager_config, mcp_manager, a2a_manager, tool_progress_reporter
    ):
        """Create tool manager fixture"""

        return ToolManager(
            logger=self.logger,
            config=tool_manager_config,
            event=self.event,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
        )

    def test_tool_manager_initialization(self, tool_manager):
        """Test tool manager is initialized correctly"""
        assert tool_manager is not None

        assert (
            len(tool_manager.get_tools()) >= 2
        )  # Should have both internal and MCP tools

    def test_tool_manager_has_both_tool_types(self, tool_manager):
        """Test that tool manager contains both MCP and internal tools"""
        tools = tool_manager.get_tools()
        tool_names = [tool.name for tool in tools]

        # Should contain internal search tool
        assert "internal_search" in tool_names

        # Should contain MCP tool (wrapped)
        assert "mcp_test_tool" in tool_names

        # Should have at least 2 tools total
        assert len(tools) >= 2

    def test_tool_manager_can_get_tools_by_name(self, tool_manager):
        """Test that tool manager can retrieve tools by name"""
        # Test getting internal tool
        internal_tool = tool_manager.get_tool_by_name("internal_search")
        assert internal_tool is not None
        assert internal_tool.name == "internal_search"

        # Test getting MCP tool
        mcp_tool = tool_manager.get_tool_by_name("mcp_test_tool")
        assert mcp_tool is not None
        assert mcp_tool.name == "mcp_test_tool"

    def test_tool_manager_tools_property_contains_both_types(self, tool_manager):
        """Test that the _tools property contains both internal and MCP tools"""
        # Access the private _tools attribute directly to verify integration
        tools = tool_manager._tools
        tool_names = [tool.name for tool in tools]

        # Verify both tool types are present
        assert "internal_search" in tool_names, (
            f"Internal tool missing. Available tools: {tool_names}"
        )
        assert "mcp_test_tool" in tool_names, (
            f"MCP tool missing. Available tools: {tool_names}"
        )

        # Verify we have the expected number of tools
        assert len(tools) == 2, f"Expected 2 tools, got {len(tools)}: {tool_names}"

    def test_tool_manager_logs_loaded_tools(self, tool_manager, caplog):
        """Test that tool manager logs the loaded tools correctly"""
        with caplog.at_level(logging.INFO):
            tool_manager.log_loaded_tools()

        # Check that both tools are mentioned in the logs
        log_output = caplog.text
        assert "internal_search" in log_output
        assert "mcp_test_tool" in log_output

    def test_tool_manager_gets_tool_definitions(self, tool_manager):
        """Test that tool manager returns tool definitions for both tool types"""
        definitions = tool_manager.get_tool_definitions()

        # Should have definitions for both tools
        assert len(definitions) == 2

        definition_names = [defn.name for defn in definitions]
        assert "internal_search" in definition_names
        assert "mcp_test_tool" in definition_names

    def test_init_tools_method(
        self, tool_manager_config, mcp_manager, tool_progress_reporter
    ):
        """Test the _init__tools method behavior with different scenarios"""

        # Test 1: Normal initialization with both tool types

        a2a_manager = A2AManager(
            logger=self.logger,
            tool_progress_reporter=tool_progress_reporter,
        )

        tool_manager = ToolManager(
            logger=self.logger,
            config=tool_manager_config,
            event=self.event,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
        )

        # Verify both tools are loaded
        tools = tool_manager.get_tools()
        tool_names = [tool.name for tool in tools]
        assert "internal_search" in tool_names
        assert "mcp_test_tool" in tool_names
        assert len(tools) == 2

    def test_init_tools_with_disabled_tools(
        self, tool_manager_config, mcp_manager, tool_progress_reporter
    ):
        """Test _init__tools method when some tools are disabled"""

        # Modify event to disable the internal search tool
        event_with_disabled = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )
        event_with_disabled.payload.tool_choices = ["internal_search", "mcp_test_tool"]
        event_with_disabled.payload.disabled_tools = ["internal_search"]

        a2a_manager = A2AManager(
            logger=self.logger,
            tool_progress_reporter=tool_progress_reporter,
        )

        tool_manager = ToolManager(
            logger=self.logger,
            config=tool_manager_config,
            event=event_with_disabled,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
        )

        # Should only have MCP tool, internal tool should be filtered out
        tools = tool_manager.get_tools()
        tool_names = [tool.name for tool in tools]
        assert "internal_search" not in tool_names
        assert "mcp_test_tool" in tool_names
        assert len(tools) == 1

    def test_init_tools_with_limited_tool_choices(
        self, tool_manager_config, mcp_manager, tool_progress_reporter
    ):
        """Test _init__tools method when only specific tools are chosen"""

        # Modify event to only choose internal search tool
        event_with_limited_choices = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )
        event_with_limited_choices.payload.tool_choices = ["internal_search"]
        event_with_limited_choices.payload.disabled_tools = []

        a2a_manager = A2AManager(
            logger=self.logger,
            tool_progress_reporter=tool_progress_reporter,
        )

        tool_manager = ToolManager(
            logger=self.logger,
            config=tool_manager_config,
            event=event_with_limited_choices,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
        )

        # Should only have internal search tool
        tools = tool_manager.get_tools()
        tool_names = [tool.name for tool in tools]
        assert "internal_search" in tool_names
        assert "mcp_test_tool" not in tool_names
        assert len(tools) == 1

    def test_init_tools_with_exclusive_tool(self, mcp_manager, tool_progress_reporter):
        """Test _init__tools method when an exclusive tool is present"""

        # Create an exclusive tool configuration
        exclusive_tool_config = ToolBuildConfig(
            name="internal_search",
            configuration=MockInternalSearchConfig(),
            display_name="Internal Search",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=True,  # Make it exclusive
            is_enabled=True,
        )

        config_with_exclusive = ToolManagerConfig(
            tools=[exclusive_tool_config], max_tool_calls=10
        )

        a2a_manager = A2AManager(
            logger=self.logger,
            tool_progress_reporter=tool_progress_reporter,
        )

        tool_manager = ToolManager(
            logger=self.logger,
            config=config_with_exclusive,
            event=self.event,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
        )

        # Should only have the exclusive tool, MCP tools should be ignored
        tools = tool_manager.get_tools()
        tool_names = [tool.name for tool in tools]
        assert "internal_search" not in tool_names
        assert "mcp_test_tool" in tool_names
        assert len(tools) == 1

    def test_init_tools_with_disabled_tool_config(
        self, mcp_manager, tool_progress_reporter
    ):
        """Test _init__tools method when a tool is disabled in its configuration"""

        # Create a disabled tool configuration
        disabled_tool_config = ToolBuildConfig(
            name="internal_search",
            configuration=MockInternalSearchConfig(),
            display_name="Internal Search",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=False,  # Disable the tool
        )

        config_with_disabled = ToolManagerConfig(
            tools=[disabled_tool_config], max_tool_calls=10
        )

        a2a_manager = A2AManager(
            logger=self.logger,
            tool_progress_reporter=tool_progress_reporter,
        )

        tool_manager = ToolManager(
            logger=self.logger,
            config=config_with_disabled,
            event=self.event,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
        )

        # Should only have MCP tool, disabled internal tool should be filtered out
        tools = tool_manager.get_tools()
        tool_names = [tool.name for tool in tools]
        assert "internal_search" not in tool_names
        assert "mcp_test_tool" in tool_names
        assert len(tools) == 1
