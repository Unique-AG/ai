"""
Test suite for MCPToolWrapper class.

This test suite validates the MCPToolWrapper's ability to:
1. Wrap MCP tools and provide proper tool descriptions
2. Handle tool execution via SDK
3. Extract and validate arguments in various formats
4. Handle errors gracefully
5. Report progress during tool execution
6. Convert JSON schema types to Python types
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig
from unique_toolkit.agentic.tools.mcp.tool_wrapper import MCPToolWrapper
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app.schemas import ChatEvent, McpServer, McpTool
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


@pytest.fixture
def mock_mcp_tool() -> McpTool:
    """Create a mock MCP tool for testing."""
    return McpTool(
        name="test_mcp_tool",
        description="A test MCP tool",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Result limit"},
            },
            "required": ["query"],
        },
        output_schema={"type": "object"},
        system_prompt="System prompt for test tool",
        user_prompt="User prompt for test tool",
        tool_format_information="Format information for test tool",
        is_connected=True,
    )


@pytest.fixture
def mock_mcp_server() -> McpServer:
    """Create a mock MCP server for testing."""
    return McpServer(
        id="server_123",
        name="Test MCP Server",
        system_prompt="Server system prompt",
        user_prompt="Server user prompt",
        tools=[],
    )


@pytest.fixture
def mock_mcp_tool_config() -> MCPToolConfig:
    """Create a mock MCP tool configuration."""
    return MCPToolConfig(
        server_id="server_123",
        server_name="Test MCP Server",
        server_system_prompt="Server system prompt",
        server_user_prompt="Server user prompt",
        mcp_source_id="source_123",
    )


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
def mcp_tool_wrapper(
    mock_mcp_server: McpServer,
    mock_mcp_tool: McpTool,
    mock_mcp_tool_config: MCPToolConfig,
    mock_chat_event: ChatEvent,
) -> MCPToolWrapper:
    """Create an MCPToolWrapper instance for testing."""
    return MCPToolWrapper(
        mcp_server=mock_mcp_server,
        mcp_tool=mock_mcp_tool,
        config=mock_mcp_tool_config,
        event=mock_chat_event,
    )


class TestMCPToolWrapperInitialization:
    """Test suite for MCPToolWrapper initialization."""

    @pytest.mark.ai
    def test_init__sets_correct_attributes__with_valid_inputs_AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool: McpTool,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify that MCPToolWrapper initializes with correct attributes.
        Why this matters: Proper initialization ensures the wrapper has access to all necessary data.
        Setup summary: Create wrapper with mocks, verify attributes are set correctly.
        """
        # Act
        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=mock_mcp_tool,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
        )

        # Assert
        assert wrapper.name == "test_mcp_tool"
        assert wrapper._mcp_tool == mock_mcp_tool
        assert wrapper._mcp_server == mock_mcp_server
        assert wrapper.configuration == mock_mcp_tool_config

    @pytest.mark.ai
    def test_init__accepts_optional_progress_reporter__with_reporter_AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool: McpTool,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify that MCPToolWrapper can be initialized with a progress reporter.
        Why this matters: Progress reporting is optional but important for user feedback.
        Setup summary: Create wrapper with mock progress reporter (with new UI disabled), verify it's stored.
        """
        # Arrange
        mock_progress_reporter = Mock(spec=ToolProgressReporter)

        # Act - progress reporter should be stored as-is (no feature flag check in __init__)
        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=mock_mcp_tool,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        # Assert
        assert wrapper._tool_progress_reporter == mock_progress_reporter


class TestMCPToolWrapperToolDescription:
    """Test suite for tool description methods."""

    @pytest.mark.ai
    def test_tool_description__returns_correct_schema__with_valid_tool_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
        mock_mcp_tool: McpTool,
    ) -> None:
        """
        Purpose: Verify that tool_description returns proper LanguageModelToolDescription.
        Why this matters: Tool descriptions are used by LLMs to understand how to call tools.
        Setup summary: Call tool_description, verify structure and content.
        """
        # Act
        description = mcp_tool_wrapper.tool_description()

        # Assert
        assert isinstance(description, LanguageModelToolDescription)
        assert description.name == "test_mcp_tool"
        assert description.description == "A test MCP tool"
        assert description.parameters == mock_mcp_tool.input_schema

    @pytest.mark.ai
    def test_tool_description__handles_missing_description__with_none_AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify that tool_description handles tools with no description gracefully.
        Why this matters: Not all MCP tools may have descriptions defined.
        Setup summary: Create tool without description, verify empty string is used.
        """
        # Arrange
        tool_without_description = McpTool(
            name="tool_no_desc",
            description=None,
            input_schema={"type": "object"},
            is_connected=True,
        )
        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=tool_without_description,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
        )

        # Act
        description = wrapper.tool_description()

        # Assert
        assert description.description == ""

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__includes_server_and_tool_info__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify system prompt includes both server and tool information.
        Why this matters: System prompts provide context to LLMs about tool capabilities.
        Setup summary: Call method, verify output contains expected sections.
        """
        # Act
        system_prompt = mcp_tool_wrapper.tool_description_for_system_prompt()

        # Assert
        assert "**MCP Server**: Test MCP Server" in system_prompt
        assert "**Tool Name**: test_mcp_tool" in system_prompt
        assert "System prompt for test tool" in system_prompt

    @pytest.mark.ai
    def test_tool_description_for_user_prompt__returns_user_prompt__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify user prompt is correctly returned.
        Why this matters: User prompts provide guidance on tool usage.
        Setup summary: Call method, verify it returns the tool's user prompt.
        """
        # Act
        user_prompt = mcp_tool_wrapper.tool_description_for_user_prompt()

        # Assert
        assert user_prompt == "User prompt for test tool"

    @pytest.mark.ai
    def test_tool_description_for_user_prompt__returns_empty_string__when_none_AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify empty string is returned when user_prompt is None.
        Why this matters: Handles optional fields gracefully.
        Setup summary: Create tool without user_prompt, verify empty string returned.
        """
        # Arrange
        tool_no_user_prompt = McpTool(
            name="tool_no_user",
            input_schema={"type": "object"},
            user_prompt=None,
            is_connected=True,
        )
        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=tool_no_user_prompt,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
        )

        # Act
        user_prompt = wrapper.tool_description_for_user_prompt()

        # Assert
        assert user_prompt == ""

    @pytest.mark.ai
    def test_tool_format_information_for_system_prompt__returns_format_info__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify format information is correctly returned.
        Why this matters: Format information guides LLMs on output structure.
        Setup summary: Call method, verify it returns tool format information.
        """
        # Act
        format_info = mcp_tool_wrapper.tool_format_information_for_system_prompt()

        # Assert
        assert format_info == "Format information for test tool"

    @pytest.mark.ai
    def test_tool_format_information_for_user_prompt__returns_empty_string__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify tool_format_information_for_user_prompt returns empty string.
        Why this matters: MCP tools don't provide user-facing format information.
        Setup summary: Call method, verify empty string is returned.
        """
        # Act
        format_info = mcp_tool_wrapper.tool_format_information_for_user_prompt()

        # Assert
        assert format_info == ""


class TestMCPToolWrapperEvaluation:
    """Test suite for evaluation-related methods."""

    @pytest.mark.ai
    def test_evaluation_check_list__returns_empty_list__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify evaluation_check_list returns empty list for MCP tools.
        Why this matters: MCP tools don't currently have evaluation metrics defined.
        Setup summary: Call method, verify empty list is returned.
        """
        # Act
        check_list = mcp_tool_wrapper.evaluation_check_list()

        # Assert
        assert check_list == []

    @pytest.mark.ai
    def test_get_evaluation_checks_based_on_tool_response__returns_empty_list__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify evaluation checks based on response returns empty list.
        Why this matters: MCP tools don't have response-based evaluation yet.
        Setup summary: Create mock response, call method, verify empty list.
        """
        # Arrange
        mock_response = ToolCallResponse(
            id="test_id",
            name="test_mcp_tool",
            content="test content",
            debug_info={},
            error_message="",
        )

        # Act
        checks = mcp_tool_wrapper.get_evaluation_checks_based_on_tool_response(
            mock_response
        )

        # Assert
        assert checks == []


class TestMCPToolWrapperArgumentExtraction:
    """Test suite for argument extraction and validation."""

    @pytest.mark.ai
    def test_extract_arguments__parses_json_string__with_valid_json_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify arguments are correctly parsed from JSON string.
        Why this matters: OpenAI API returns arguments as JSON strings.
        Setup summary: Create tool call with JSON string arguments, verify parsing.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments='{"query": "test search", "limit": 10}',
        )

        # Act
        arguments = mcp_tool_wrapper._extract_and_validate_arguments(tool_call)

        # Assert
        assert arguments == {"query": "test search", "limit": 10}

    @pytest.mark.ai
    def test_extract_arguments__handles_dict_arguments__with_dict_input_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify arguments are correctly handled when already a dict.
        Why this matters: Internal processing may provide arguments as dicts.
        Setup summary: Create tool call with dict arguments, verify pass-through.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test search", "limit": 10},
        )

        # Act
        arguments = mcp_tool_wrapper._extract_and_validate_arguments(tool_call)

        # Assert
        assert arguments == {"query": "test search", "limit": 10}

    @pytest.mark.ai
    def test_extract_arguments__returns_empty_dict__with_none_arguments_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify empty dict is returned when arguments are None.
        Why this matters: Handles edge case of tools with no required arguments.
        Setup summary: Create tool call with None arguments, verify empty dict returned.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments=None,
        )

        # Act
        arguments = mcp_tool_wrapper._extract_and_validate_arguments(tool_call)

        # Assert
        assert arguments == {}

    @pytest.mark.ai
    def test_extract_arguments__returns_empty_dict__with_empty_string_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify empty dict is returned when arguments are empty string.
        Why this matters: Handles edge case of malformed API responses.
        Setup summary: Create tool call with empty string arguments, verify empty dict.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={},
        )

        # Act
        arguments = mcp_tool_wrapper._extract_and_validate_arguments(tool_call)

        # Assert
        assert arguments == {}


class TestMCPToolWrapperJsonSchemaConversion:
    """Test suite for JSON schema to Python type conversion."""

    @pytest.mark.ai
    def test_json_schema_to_python_type__converts_string__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify string JSON type is converted to Python str.
        Why this matters: Type conversion enables proper type checking.
        Setup summary: Call method with string schema, verify str type returned.
        """
        # Act
        python_type = mcp_tool_wrapper._json_schema_to_python_type({"type": "string"})

        # Assert
        assert python_type is str

    @pytest.mark.ai
    def test_json_schema_to_python_type__converts_integer__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify integer JSON type is converted to Python int.
        Why this matters: Numeric type conversion is essential for validation.
        Setup summary: Call method with integer schema, verify int type returned.
        """
        # Act
        python_type = mcp_tool_wrapper._json_schema_to_python_type({"type": "integer"})

        # Assert
        assert python_type is int

    @pytest.mark.ai
    def test_json_schema_to_python_type__converts_number__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify number JSON type is converted to Python float.
        Why this matters: Handles decimal numbers correctly.
        Setup summary: Call method with number schema, verify float type returned.
        """
        # Act
        python_type = mcp_tool_wrapper._json_schema_to_python_type({"type": "number"})

        # Assert
        assert python_type is float

    @pytest.mark.ai
    def test_json_schema_to_python_type__converts_boolean__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify boolean JSON type is converted to Python bool.
        Why this matters: Boolean handling is essential for flags and switches.
        Setup summary: Call method with boolean schema, verify bool type returned.
        """
        # Act
        python_type = mcp_tool_wrapper._json_schema_to_python_type({"type": "boolean"})

        # Assert
        assert python_type is bool

    @pytest.mark.ai
    def test_json_schema_to_python_type__converts_array__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify array JSON type is converted to Python list.
        Why this matters: List handling is essential for collections.
        Setup summary: Call method with array schema, verify list type returned.
        """
        # Act
        python_type = mcp_tool_wrapper._json_schema_to_python_type({"type": "array"})

        # Assert
        assert python_type is list

    @pytest.mark.ai
    def test_json_schema_to_python_type__converts_object__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify object JSON type is converted to Python dict.
        Why this matters: Object handling is essential for complex structures.
        Setup summary: Call method with object schema, verify dict type returned.
        """
        # Act
        python_type = mcp_tool_wrapper._json_schema_to_python_type({"type": "object"})

        # Assert
        assert python_type is dict

    @pytest.mark.ai
    def test_json_schema_to_python_type__defaults_to_string__with_unknown_type_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify unknown types default to str.
        Why this matters: Provides safe fallback for unsupported types.
        Setup summary: Call method with unknown type, verify str is returned.
        """
        # Act
        python_type = mcp_tool_wrapper._json_schema_to_python_type(
            {"type": "unknown_type"}
        )

        # Assert
        assert python_type is str

    @pytest.mark.ai
    def test_json_schema_to_python_type__defaults_to_string__with_missing_type_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify missing type defaults to str.
        Why this matters: Handles incomplete schemas gracefully.
        Setup summary: Call method with empty schema, verify str is returned.
        """
        # Act
        python_type = mcp_tool_wrapper._json_schema_to_python_type({})

        # Assert
        assert python_type is str


class TestMCPToolWrapperRun:
    """Test suite for tool execution."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__executes_successfully__with_valid_input_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify tool executes successfully with valid input.
        Why this matters: Core functionality of the wrapper is tool execution.
        Setup summary: Mock SDK call, execute tool, verify response.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch.object(mcp_tool_wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {"result": "success", "data": [1, 2, 3]}

            # Act
            response: ToolCallResponse = await mcp_tool_wrapper.run(tool_call)

            # Assert
            assert isinstance(response, ToolCallResponse)
            assert response.id == "call_123"
            assert response.name == "test_mcp_tool"
            assert response.error_message == ""
            assert json.loads(response.content) == {
                "result": "success",
                "data": [1, 2, 3],
            }
            assert response.debug_info is not None
            assert response.debug_info["mcp_tool"] == "test_mcp_tool"
            assert response.debug_info["arguments"] is not None
            assert response.debug_info["arguments"] == {"query": "test"}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__calls_sdk_with_correct_parameters__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify SDK is called with correct parameters from event.
        Why this matters: Ensures proper integration with backend API.
        Setup summary: Mock SDK call, execute tool, verify SDK call parameters.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test", "limit": 5},
        )

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch.object(mcp_tool_wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {"result": "ok"}

            # Act
            await mcp_tool_wrapper.run(tool_call)

            # Assert
            mock_sdk_call.assert_called_once_with(
                user_id="user_123",
                company_id="company_456",
                name="test_mcp_tool",
                messageId="assistant_message_202",
                chatId=mock_chat_event.payload.chat_id,
                arguments={"query": "test", "limit": 5},
            )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__handles_sdk_exception__with_error_response_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify tool handles SDK exceptions gracefully.
        Why this matters: Errors should be captured and returned, not propagated.
        Setup summary: Mock SDK to raise exception, execute tool, verify error response.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch.object(mcp_tool_wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.side_effect = Exception("SDK error occurred")

            # Act
            response = await mcp_tool_wrapper.run(tool_call)

            # Assert
            assert isinstance(response, ToolCallResponse)
            assert response.id == "call_123"
            assert response.name == "test_mcp_tool"
            assert response.error_message == "SDK error occurred"
            assert response.debug_info is not None
            assert response.debug_info["mcp_tool"] == "test_mcp_tool"
            assert response.debug_info["error"] == "SDK error occurred"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__notifies_progress_reporter__when_new_ui_disabled_AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool: McpTool,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify progress reporter is notified during execution when new UI is disabled.
        Why this matters: Progress reporting provides user feedback in legacy UI.
        Setup summary: Create wrapper with mock reporter (with new UI disabled), execute tool, verify notifications.
        """
        # Arrange
        mock_progress_reporter = Mock(spec=ToolProgressReporter)
        mock_progress_reporter.notify_from_tool_call = AsyncMock()

        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=mock_mcp_tool,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        # Mock feature flags to return False (new UI disabled)
        mock_feature_flags = Mock()
        mock_feature_flags.is_new_answers_ui_enabled.return_value = False

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch(
                "unique_toolkit.agentic.tools.mcp.tool_wrapper.feature_flags",
                mock_feature_flags,
            ),
            patch.object(wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {"result": "ok"}

            # Act
            await wrapper.run(tool_call)

            # Assert
            assert mock_progress_reporter.notify_from_tool_call.call_count == 2

            # Check RUNNING notification
            first_call = mock_progress_reporter.notify_from_tool_call.call_args_list[0]
            assert first_call.kwargs["state"] == ProgressState.RUNNING
            assert "Executing MCP tool" in first_call.kwargs["message"]

            # Check FINISHED notification
            second_call = mock_progress_reporter.notify_from_tool_call.call_args_list[1]
            assert second_call.kwargs["state"] == ProgressState.FINISHED
            assert "completed" in second_call.kwargs["message"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__skips_progress_notifications__when_new_ui_enabled_AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool: McpTool,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify progress reporter is NOT notified when new UI is enabled.
        Why this matters: New UI has different progress tracking mechanism.
        Setup summary: Create wrapper with mock reporter (with new UI enabled), execute tool, verify no notifications.
        """
        # Arrange
        mock_progress_reporter = Mock(spec=ToolProgressReporter)
        mock_progress_reporter.notify_from_tool_call = AsyncMock()

        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=mock_mcp_tool,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        # Mock feature flags to return True (new UI enabled)
        mock_feature_flags = Mock()
        mock_feature_flags.is_new_answers_ui_enabled.return_value = True

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch(
                "unique_toolkit.agentic.tools.mcp.tool_wrapper.feature_flags",
                mock_feature_flags,
            ),
            patch.object(wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {"result": "ok"}

            # Act
            response = await wrapper.run(tool_call)

            # Assert - tool should still execute successfully
            assert response.error_message == ""
            assert response.name == "test_mcp_tool"

            # But progress reporter should NOT be called (new UI is enabled)
            assert mock_progress_reporter.notify_from_tool_call.call_count == 0

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__skips_progress_notifications_on_error__when_new_ui_enabled_AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool: McpTool,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify progress reporter is NOT notified on failure when new UI is enabled.
        Why this matters: New UI has different error tracking mechanism.
        Setup summary: Create wrapper with reporter (with new UI enabled), cause failure, verify no notifications.
        """
        # Arrange
        mock_progress_reporter = Mock(spec=ToolProgressReporter)
        mock_progress_reporter.notify_from_tool_call = AsyncMock()

        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=mock_mcp_tool,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        # Mock feature flags to return True (new UI enabled)
        mock_feature_flags = Mock()
        mock_feature_flags.is_new_answers_ui_enabled.return_value = True

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch(
                "unique_toolkit.agentic.tools.mcp.tool_wrapper.feature_flags",
                mock_feature_flags,
            ),
            patch.object(wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.side_effect = Exception("Test error")

            # Act
            response = await wrapper.run(tool_call)

            # Assert - error should still be captured in response
            assert response.error_message == "Test error"

            # But progress reporter should NOT be called (new UI is enabled)
            assert mock_progress_reporter.notify_from_tool_call.call_count == 0

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__notifies_progress_reporter_on_error__when_new_ui_disabled_AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool: McpTool,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify progress reporter is notified on failure when new UI is disabled.
        Why this matters: Users need feedback even when tools fail in legacy UI.
        Setup summary: Create wrapper with reporter (with new UI disabled), cause failure, verify notification.
        """
        # Arrange
        mock_progress_reporter = Mock(spec=ToolProgressReporter)
        mock_progress_reporter.notify_from_tool_call = AsyncMock()

        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=mock_mcp_tool,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        # Mock feature flags to return False (new UI disabled)
        mock_feature_flags = Mock()
        mock_feature_flags.is_new_answers_ui_enabled.return_value = False

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch(
                "unique_toolkit.agentic.tools.mcp.tool_wrapper.feature_flags",
                mock_feature_flags,
            ),
            patch.object(wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.side_effect = Exception("Test error")

            # Act
            await wrapper.run(tool_call)

            # Assert
            assert mock_progress_reporter.notify_from_tool_call.call_count == 2

            # Check FAILED notification
            second_call = mock_progress_reporter.notify_from_tool_call.call_args_list[1]
            assert second_call.kwargs["state"] == ProgressState.FAILED
            assert "failed" in second_call.kwargs["message"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__checks_feature_flag_with_company_id__AI(
        self,
        mock_mcp_server: McpServer,
        mock_mcp_tool: McpTool,
        mock_mcp_tool_config: MCPToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify feature flag is checked with the correct company_id from the event during run.
        Why this matters: Feature flags are company-specific.
        Setup summary: Create wrapper, run tool, verify feature flag is called with correct company_id.
        """
        # Arrange
        mock_progress_reporter = Mock(spec=ToolProgressReporter)
        mock_progress_reporter.notify_from_tool_call = AsyncMock()

        wrapper = MCPToolWrapper(
            mcp_server=mock_mcp_server,
            mcp_tool=mock_mcp_tool,
            config=mock_mcp_tool_config,
            event=mock_chat_event,
            tool_progress_reporter=mock_progress_reporter,
        )

        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        # Mock feature flags to track calls
        mock_feature_flags = Mock()
        mock_feature_flags.is_new_answers_ui_enabled.return_value = False

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch(
                "unique_toolkit.agentic.tools.mcp.tool_wrapper.feature_flags",
                mock_feature_flags,
            ),
            patch.object(wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {"result": "ok"}

            # Act
            await wrapper.run(tool_call)

            # Assert - feature flag should be called with the company_id from the event
            mock_feature_flags.is_new_answers_ui_enabled.assert_called_with(
                "company_456"
            )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__works_without_progress_reporter__with_none_reporter_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify tool works without progress reporter.
        Why this matters: Progress reporter is optional functionality.
        Setup summary: Execute tool without reporter, verify success.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch.object(mcp_tool_wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {"result": "ok"}

            # Act
            response = await mcp_tool_wrapper.run(tool_call)

            # Assert
            assert response.error_message == ""
            assert response.name == "test_mcp_tool"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__preserves_tool_call_id__in_response_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify tool call ID is preserved in response.
        Why this matters: ID tracking is essential for matching requests to responses.
        Setup summary: Execute tool with specific ID, verify ID in response.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="unique_call_id_789",
            name="test_mcp_tool",
            arguments='{"query": "test"}',
        )

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch.object(mcp_tool_wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {"result": "ok"}

            # Act
            response = await mcp_tool_wrapper.run(tool_call)

            # Assert
            assert response.id == "unique_call_id_789"


class TestMCPToolWrapperCallSDK:
    """Test suite for SDK call method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call_mcp_tool_via_sdk__returns_result__with_successful_call_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify _call_mcp_tool_via_sdk returns SDK result.
        Why this matters: Direct SDK integration is core functionality.
        Setup summary: Mock SDK, call method, verify result.
        """
        # Arrange
        arguments = {"query": "test search"}

        with patch("unique_sdk.MCP.call_tool") as mock_sdk_call:
            mock_sdk_call.return_value = {"status": "success", "items": []}

            # Act
            result = await mcp_tool_wrapper._call_mcp_tool_via_sdk(arguments)

            # Assert
            assert result == {"status": "success", "items": []}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call_mcp_tool_via_sdk__raises_exception__on_sdk_error_AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify SDK errors are propagated.
        Why this matters: Allows higher-level error handling.
        Setup summary: Mock SDK to raise exception, verify it's propagated.
        """
        # Arrange
        arguments = {"query": "test"}

        with patch("unique_sdk.MCP.call_tool") as mock_sdk_call:
            mock_sdk_call.side_effect = Exception("Connection timeout")

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await mcp_tool_wrapper._call_mcp_tool_via_sdk(arguments)

            assert "Connection timeout" in str(exc_info.value)


class TestMCPToolWrapperEdgeCases:
    """Test suite for edge cases and unusual scenarios."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__handles_empty_sdk_response__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify tool handles empty SDK responses.
        Why this matters: Some tools may return empty results.
        Setup summary: Mock SDK to return empty dict, verify handling.
        """
        # Arrange
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments={"query": "test"},
        )

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch.object(mcp_tool_wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {}

            # Act
            response = await mcp_tool_wrapper.run(tool_call)

            # Assert
            assert response.error_message == ""
            assert json.loads(response.content) == {}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__handles_complex_nested_arguments__AI(
        self,
        mcp_tool_wrapper: MCPToolWrapper,
    ) -> None:
        """
        Purpose: Verify tool handles complex nested argument structures.
        Why this matters: Real-world tools often have complex parameters.
        Setup summary: Execute with nested arguments, verify proper handling.
        """
        # Arrange
        complex_args = {
            "query": "test",
            "filters": {
                "date": {"start": "2023-01-01", "end": "2023-12-31"},
                "categories": ["cat1", "cat2"],
            },
            "pagination": {"page": 1, "size": 20},
        }
        tool_call = LanguageModelFunction(
            id="call_123",
            name="test_mcp_tool",
            arguments=complex_args,
        )

        with (
            patch("unique_sdk.MCP.call_tool") as mock_sdk_call,
            patch.object(mcp_tool_wrapper, "_create_or_update_message_log"),
        ):
            mock_sdk_call.return_value = {"result": "ok"}

            # Act
            response = await mcp_tool_wrapper.run(tool_call)

            # Assert
            assert response.error_message == ""
            mock_sdk_call.assert_called_once()
            called_args = mock_sdk_call.call_args[1]["arguments"]
            assert called_args == complex_args
