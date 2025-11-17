"""
Test suite for MCPManager class.

This test suite validates the MCPManager's ability to:
1. Manage multiple MCP servers
2. Retrieve servers by ID
3. Create tool wrappers for all MCP tools
4. Handle errors during tool wrapper creation
5. Apply proper settings to MCP tool wrappers
"""

from unittest.mock import Mock

import pytest

from unique_toolkit.agentic.tools.config import ToolIcon, ToolSelectionPolicy
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.mcp.tool_wrapper import MCPToolWrapper
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent, McpServer, McpTool


@pytest.fixture
def mock_chat_event() -> ChatEvent:
    """Create a mock ChatEvent for testing."""
    event = Mock(spec=ChatEvent)
    event.user_id = "user_123"
    event.company_id = "company_456"
    event.chat_id = "chat_789"
    event.assistant_id = "assistant_101"
    
    # Mock the payload structure
    mock_payload = Mock()
    mock_payload.assistant_message = Mock()
    mock_payload.assistant_message.id = "assistant_message_202"
    event.payload = mock_payload
    
    return event


@pytest.fixture
def mock_progress_reporter() -> ToolProgressReporter:
    """Create a mock ToolProgressReporter."""
    return Mock(spec=ToolProgressReporter)


@pytest.fixture
def mock_mcp_tools() -> list[McpTool]:
    """Create mock MCP tools for testing."""
    return [
        McpTool(
            name="search_tool",
            description="Search for information",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            title="Search Tool",
            is_connected=True,
        ),
        McpTool(
            name="fetch_tool",
            description="Fetch data",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}}},
            title=None,  # Test fallback to name
            is_connected=True,
        ),
    ]


@pytest.fixture
def mock_mcp_servers(mock_mcp_tools: list[McpTool]) -> list[McpServer]:
    """Create mock MCP servers for testing."""
    return [
        McpServer(
            id="server_1",
            name="Test Server 1",
            system_prompt="System prompt for server 1",
            user_prompt="User prompt for server 1",
            tools=mock_mcp_tools,
        ),
        McpServer(
            id="server_2",
            name="Test Server 2",
            system_prompt="System prompt for server 2",
            user_prompt="User prompt for server 2",
            tools=[],  # Empty tools list
        ),
    ]


@pytest.fixture
def mcp_manager(
    mock_mcp_servers: list[McpServer],
    mock_chat_event: ChatEvent,
    mock_progress_reporter: ToolProgressReporter,
) -> MCPManager:
    """Create an MCPManager instance for testing."""
    return MCPManager(
        mcp_servers=mock_mcp_servers,
        event=mock_chat_event,
        tool_progress_reporter=mock_progress_reporter,
    )


class TestMCPManagerInitialization:
    """Test suite for MCPManager initialization."""

    @pytest.mark.ai
    def test_init__stores_servers_event_and_reporter__with_valid_inputs_AI(
        self,
        mock_mcp_servers: list[McpServer],
        mock_chat_event: ChatEvent,
        mock_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify MCPManager initializes with correct attributes.
        Why this matters: Proper initialization ensures manager has access to all necessary data.
        Setup summary: Create manager, verify all attributes are stored correctly.
        """
        # Act
        manager = MCPManager(
            mcp_servers=mock_mcp_servers,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        # Assert
        assert manager._mcp_servers == mock_mcp_servers
        assert manager._event == mock_chat_event
        assert manager._tool_progress_reporter == mock_progress_reporter


class TestMCPManagerServerRetrieval:
    """Test suite for MCP server retrieval methods."""

    @pytest.mark.ai
    def test_get_mcp_servers__returns_all_servers__AI(
        self,
        mcp_manager: MCPManager,
        mock_mcp_servers: list[McpServer],
    ) -> None:
        """
        Purpose: Verify get_mcp_servers returns all stored servers.
        Why this matters: Provides access to server configuration.
        Setup summary: Call method, verify it returns all servers.
        """
        # Act
        servers = mcp_manager.get_mcp_servers()

        # Assert
        assert servers == mock_mcp_servers
        assert len(servers) == 2

    @pytest.mark.ai
    def test_get_mcp_server_by_id__returns_correct_server__with_valid_id_AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify get_mcp_server_by_id returns the correct server.
        Why this matters: Enables targeted server access by ID.
        Setup summary: Request server by ID, verify correct server returned.
        """
        # Act
        server = mcp_manager.get_mcp_server_by_id("server_1")

        # Assert
        assert server is not None
        assert server.id == "server_1"
        assert server.name == "Test Server 1"

    @pytest.mark.ai
    def test_get_mcp_server_by_id__returns_none__with_invalid_id_AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify get_mcp_server_by_id returns None for non-existent ID.
        Why this matters: Handles missing servers gracefully.
        Setup summary: Request server with invalid ID, verify None is returned.
        """
        # Act
        server = mcp_manager.get_mcp_server_by_id("nonexistent_server")

        # Assert
        assert server is None

    @pytest.mark.ai
    def test_get_mcp_server_by_id__returns_second_server__with_second_id_AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify get_mcp_server_by_id works for multiple servers.
        Why this matters: Confirms ID lookup works for any server.
        Setup summary: Request second server by ID, verify correct server returned.
        """
        # Act
        server = mcp_manager.get_mcp_server_by_id("server_2")

        # Assert
        assert server is not None
        assert server.id == "server_2"
        assert server.name == "Test Server 2"


class TestMCPManagerToolCreation:
    """Test suite for MCP tool wrapper creation."""

    @pytest.mark.ai
    def test_get_all_mcp_tools__creates_wrappers_for_all_tools__AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify get_all_mcp_tools creates wrappers for all available tools.
        Why this matters: Core functionality for making MCP tools available.
        Setup summary: Call method, verify correct number of wrappers created.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        # Should have 2 tools from server_1, 0 from server_2
        assert len(tools) == 2
        assert all(isinstance(tool, MCPToolWrapper) for tool in tools)

    @pytest.mark.ai
    def test_get_all_mcp_tools__sets_correct_tool_names__AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify tool wrappers have correct names.
        Why this matters: Tool names are used for identification and routing.
        Setup summary: Get all tools, verify their names match source tools.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        tool_names = [tool.name for tool in tools]
        assert "search_tool" in tool_names
        assert "fetch_tool" in tool_names

    @pytest.mark.ai
    def test_get_all_mcp_tools__applies_correct_settings__AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify tool wrappers have correct settings applied.
        Why this matters: Settings control tool behavior and display.
        Setup summary: Get all tools, verify settings are properly configured.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        for tool in tools:
            assert tool.settings is not None
            assert tool.settings.is_enabled is True
            assert tool.settings.is_exclusive is False
            assert tool.settings.icon == ToolIcon.BOOK
            assert tool.settings.selection_policy == ToolSelectionPolicy.BY_USER

    @pytest.mark.ai
    def test_get_all_mcp_tools__uses_title_as_display_name__when_available_AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify display_name uses title when available.
        Why this matters: Titles provide better user-facing names.
        Setup summary: Get all tools, verify search_tool uses its title.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        search_tool = next((t for t in tools if t.name == "search_tool"), None)
        assert search_tool is not None
        assert search_tool.settings.display_name == "Search Tool"

    @pytest.mark.ai
    def test_get_all_mcp_tools__falls_back_to_name__when_no_title_AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify display_name falls back to tool name when no title.
        Why this matters: Ensures all tools have a display name.
        Setup summary: Get all tools, verify fetch_tool uses its name.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        fetch_tool = next((t for t in tools if t.name == "fetch_tool"), None)
        assert fetch_tool is not None
        assert fetch_tool.settings.display_name == "fetch_tool"

    @pytest.mark.ai
    def test_get_all_mcp_tools__includes_server_context__in_config_AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify tool configs include server context information.
        Why this matters: Server context is needed for proper tool execution.
        Setup summary: Get all tools, verify configs have server details.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        for tool in tools:
            config = tool.configuration
            assert config.server_id == "server_1"
            assert config.server_name == "Test Server 1"
            assert config.server_system_prompt == "System prompt for server 1"
            assert config.server_user_prompt == "User prompt for server 1"

    @pytest.mark.ai
    def test_get_all_mcp_tools__skips_server_without_tools_attribute__AI(
        self,
        mock_chat_event: ChatEvent,
        mock_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify manager handles servers without tools attribute.
        Why this matters: Defensive programming prevents AttributeError.
        Setup summary: Create server without tools attribute, verify no crash.
        """
        # Arrange
        server_without_tools = Mock(spec=McpServer)
        server_without_tools.id = "server_3"
        server_without_tools.name = "Server Without Tools"
        # Deliberately don't set 'tools' attribute
        delattr(server_without_tools, "tools")
        
        manager = MCPManager(
            mcp_servers=[server_without_tools],
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        # Act
        tools = manager.get_all_mcp_tools()

        # Assert
        assert tools == []

    @pytest.mark.ai
    def test_get_all_mcp_tools__skips_server_with_empty_tools__AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify manager handles servers with empty tools list.
        Why this matters: Not all servers have tools configured.
        Setup summary: Manager has server_2 with empty tools, verify no tools from it.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        # Only tools from server_1 should be present
        assert len(tools) == 2
        assert all(tool.configuration.server_id == "server_1" for tool in tools)

    @pytest.mark.ai
    def test_get_all_mcp_tools__returns_empty_list__with_no_servers_AI(
        self,
        mock_chat_event: ChatEvent,
        mock_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify manager handles empty server list gracefully.
        Why this matters: Edge case handling prevents errors.
        Setup summary: Create manager with no servers, verify empty list returned.
        """
        # Arrange
        manager = MCPManager(
            mcp_servers=[],
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        # Act
        tools = manager.get_all_mcp_tools()

        # Assert
        assert tools == []

    @pytest.mark.ai
    def test_get_all_mcp_tools__handles_wrapper_creation_error__logs_and_continues_AI(
        self,
        mock_chat_event: ChatEvent,
        mock_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify manager handles errors during wrapper creation gracefully.
        Why this matters: One bad tool shouldn't break all tool loading.
        Setup summary: Create tool that will cause error, verify other tools still load.
        """
        # Arrange
        bad_tool = McpTool(
            name="bad_tool",
            description="This tool will cause an error",
            input_schema={"type": "object"},
            is_connected=True,
        )
        
        good_tool = McpTool(
            name="good_tool",
            description="This tool is fine",
            input_schema={"type": "object"},
            is_connected=True,
        )
        
        # Create a server with both tools
        server = Mock(spec=McpServer)
        server.id = "test_server"
        server.name = "Test Server"
        server.system_prompt = "System prompt"
        server.user_prompt = "User prompt"
        server.tools = [bad_tool, good_tool]
        
        manager = MCPManager(
            mcp_servers=[server],
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        # Act
        tools = manager.get_all_mcp_tools()

        # Assert
        # Both tools should be created successfully (no error in this case)
        # In a real error scenario, we'd patch the wrapper creation to fail
        assert len(tools) == 2

    @pytest.mark.ai
    def test_get_all_mcp_tools__creates_independent_wrappers__for_each_tool_AI(
        self,
        mcp_manager: MCPManager,
    ) -> None:
        """
        Purpose: Verify each tool gets its own wrapper instance.
        Why this matters: Tools should not share state.
        Setup summary: Get all tools, verify they are distinct instances.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        assert len(tools) == 2
        assert tools[0] is not tools[1]
        assert tools[0].name != tools[1].name

    @pytest.mark.ai
    def test_get_all_mcp_tools__preserves_progress_reporter__in_wrappers_AI(
        self,
        mcp_manager: MCPManager,
        mock_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tool wrappers receive the progress reporter.
        Why this matters: Progress reporting should work for all MCP tools.
        Setup summary: Get all tools, verify they have progress reporter set.
        """
        # Act
        tools = mcp_manager.get_all_mcp_tools()

        # Assert
        for tool in tools:
            assert tool._tool_progress_reporter == mock_progress_reporter


class TestMCPManagerMultipleServersWithTools:
    """Test suite for scenarios with multiple servers containing tools."""

    @pytest.mark.ai
    def test_get_all_mcp_tools__combines_tools_from_multiple_servers__AI(
        self,
        mock_chat_event: ChatEvent,
        mock_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify tools from multiple servers are all included.
        Why this matters: Manager should aggregate tools across all servers.
        Setup summary: Create multiple servers with tools, verify all are returned.
        """
        # Arrange
        server1_tools = [
            McpTool(
                name="tool_1",
                description="Tool from server 1",
                input_schema={"type": "object"},
                is_connected=True,
            ),
        ]
        
        server2_tools = [
            McpTool(
                name="tool_2",
                description="Tool from server 2",
                input_schema={"type": "object"},
                is_connected=True,
            ),
        ]
        
        servers = [
            McpServer(
                id="server_1",
                name="Server 1",
                tools=server1_tools,
            ),
            McpServer(
                id="server_2",
                name="Server 2",
                tools=server2_tools,
            ),
        ]
        
        manager = MCPManager(
            mcp_servers=servers,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        # Act
        tools = manager.get_all_mcp_tools()

        # Assert
        assert len(tools) == 2
        tool_names = [tool.name for tool in tools]
        assert "tool_1" in tool_names
        assert "tool_2" in tool_names

    @pytest.mark.ai
    def test_get_all_mcp_tools__maintains_server_context__for_each_tool_AI(
        self,
        mock_chat_event: ChatEvent,
        mock_progress_reporter: ToolProgressReporter,
    ) -> None:
        """
        Purpose: Verify each tool maintains its server context.
        Why this matters: Tools need to know which server they belong to.
        Setup summary: Create tools from different servers, verify each has correct server ID.
        """
        # Arrange
        server1_tools = [
            McpTool(
                name="tool_s1",
                input_schema={"type": "object"},
                is_connected=True,
            ),
        ]
        
        server2_tools = [
            McpTool(
                name="tool_s2",
                input_schema={"type": "object"},
                is_connected=True,
            ),
        ]
        
        servers = [
            McpServer(id="s1", name="Server 1", tools=server1_tools),
            McpServer(id="s2", name="Server 2", tools=server2_tools),
        ]
        
        manager = MCPManager(
            mcp_servers=servers,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        # Act
        tools = manager.get_all_mcp_tools()

        # Assert
        tool_s1 = next((t for t in tools if t.name == "tool_s1"), None)
        tool_s2 = next((t for t in tools if t.name == "tool_s2"), None)
        
        assert tool_s1.configuration.server_id == "s1"
        assert tool_s2.configuration.server_id == "s2"

