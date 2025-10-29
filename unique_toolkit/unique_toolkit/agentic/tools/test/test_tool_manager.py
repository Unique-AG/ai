"""
Test suite for ToolManager classes.

This test suite validates:
1. ForcedToolOption initialization and attributes
2. ToolManagerConfig validation and defaults
3. BaseToolManager abstract functionality
4. ToolManager tool initialization, filtering, and execution
5. ResponsesApiToolManager integration with ToolManager
6. Tool call execution, parallelization, and error handling
7. Duplicate filtering and evaluation check list management
"""

from logging import Logger, getLogger
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tests.test_obj_factory import get_event_obj
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.a2a import A2AManager
from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
)
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.openai_builtin.manager import OpenAIBuiltInToolManager
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_manager import (
    BaseToolManager,
    ForcedToolOption,
    ResponsesApiToolManager,
    ToolManager,
    ToolManagerConfig,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

# ========== Fixtures ==========


@pytest.fixture
def mock_logger() -> Logger:
    """
    Fixture providing a mock logger.

    Returns:
        Logger instance for testing.
    """
    return getLogger(__name__)


@pytest.fixture
def tool_manager_config() -> ToolManagerConfig:
    """
    Base fixture for ToolManagerConfig with default values.

    Returns:
        ToolManagerConfig with empty tools list and default max_tool_calls.
    """
    return ToolManagerConfig(tools=[], max_tool_calls=10)


@pytest.fixture
def tool_manager_config_with_tools(
    mock_tool_build_config: ToolBuildConfig,
) -> ToolManagerConfig:
    """
    Fixture for ToolManagerConfig with tools configured.

    Args:
        mock_tool_build_config: Tool build configuration to include.

    Returns:
        ToolManagerConfig with a single tool configured.
    """
    return ToolManagerConfig(
        tools=[mock_tool_build_config],
        max_tool_calls=5,
    )


@pytest.fixture
def mock_chat_event() -> ChatEvent:
    """
    Fixture providing a mock ChatEvent for tool manager initialization.

    Returns:
        ChatEvent with test data and empty tool choices.
    """
    event = get_event_obj(
        user_id="test_user",
        company_id="test_company",
        chat_id="test_chat",
        assistant_id="test_assistant",
        user_message_id="test_message",
    )
    # Add tool-related attributes to payload
    event.payload.tool_choices = []
    event.payload.disabled_tools = []
    return event


@pytest.fixture
def mock_tool_progress_reporter() -> ToolProgressReporter:
    """
    Fixture providing a mock ToolProgressReporter.

    Returns:
        Mock ToolProgressReporter instance.
    """
    reporter = Mock(spec=ToolProgressReporter)
    reporter.report_progress = AsyncMock()
    return reporter


@pytest.fixture
def mock_mcp_manager() -> MCPManager:
    """
    Fixture providing a mock MCPManager.

    Returns:
        Mock MCPManager with empty tool list.
    """
    manager = Mock(spec=MCPManager)
    manager.get_all_mcp_tools = Mock(return_value=[])
    return manager


@pytest.fixture
def mock_a2a_manager() -> A2AManager:
    """
    Fixture providing a mock A2AManager.

    Returns:
        Mock A2AManager with empty sub-agents.
    """
    manager = Mock(spec=A2AManager)
    manager.get_all_sub_agents = Mock(return_value=([], []))
    return manager


@pytest.fixture
def mock_language_model_function_list() -> list[LanguageModelFunction]:
    """
    Fixture providing a list of mock LanguageModelFunction objects.

    Returns:
        List of LanguageModelFunction for testing tool execution.
    """
    return [
        LanguageModelFunction(
            id="call_1",
            name="InternalSearchTool",
            arguments='{"test_param": "value1"}',
        ),
        LanguageModelFunction(
            id="call_2",
            name="InternalSearchTool",
            arguments='{"test_param": "value2"}',
        ),
    ]


# ========== ForcedToolOption Tests ==========


class TestForcedToolOption:
    """Test suite for ForcedToolOption class."""

    def test_init__sets_name_and_type__with_valid_name(self) -> None:
        """
        Purpose: Verify ForcedToolOption initializes with correct name and type.
        Why this matters: ForcedToolOption is used to force tool selection in the agent.
        Setup summary: Create instance with name, verify attributes.
        """
        # Arrange & Act
        option = ForcedToolOption(name="my_tool")

        # Assert
        assert option.name == "my_tool"
        assert option.type == "function"


# ========== ToolManagerConfig Tests ==========


class TestToolManagerConfig:
    """Test suite for ToolManagerConfig Pydantic model."""

    def test_default_values__creates_config__with_empty_tools(self) -> None:
        """
        Purpose: Verify ToolManagerConfig uses default values when not provided.
        Why this matters: Default configuration should work without explicit parameters.
        Setup summary: Create config without args, verify defaults.
        """
        # Arrange & Act
        config = ToolManagerConfig()

        # Assert
        assert config.tools == []
        assert config.max_tool_calls == 10

    def test_custom_values__creates_config__with_provided_values(
        self, mock_tool_build_config: ToolBuildConfig
    ) -> None:
        """
        Purpose: Verify ToolManagerConfig accepts and stores custom values.
        Why this matters: Configuration must be customizable for different use cases.
        Setup summary: Create config with custom values, verify they are stored.
        """
        # Arrange & Act
        config = ToolManagerConfig(
            tools=[mock_tool_build_config],
            max_tool_calls=5,
        )

        # Assert
        assert len(config.tools) == 1
        assert config.tools[0] == mock_tool_build_config
        assert config.max_tool_calls == 5

    def test_validation__raises_error__with_invalid_max_tool_calls(self) -> None:
        """
        Purpose: Verify ToolManagerConfig validates max_tool_calls >= 1.
        Why this matters: Invalid configuration should be caught early to prevent runtime errors.
        Setup summary: Attempt to create config with max_tool_calls=0, expect validation error.
        """
        # Arrange, Act & Assert
        with pytest.raises(Exception):  # Pydantic validation error
            ToolManagerConfig(tools=[], max_tool_calls=0)


# ========== BaseToolManager Tests ==========


class TestBaseToolManager:
    """Test suite for BaseToolManager abstract base class."""

    def test_init__initializes_state__with_config(
        self, tool_manager_config: ToolManagerConfig
    ) -> None:
        """
        Purpose: Verify BaseToolManager initializes with config and empty check list.
        Why this matters: Base initialization sets up state used by all subclasses.
        Setup summary: Create concrete implementation, verify initialization.
        """

        # Arrange & Act
        class ConcreteToolManager(BaseToolManager):
            def get_tool_by_name(self, name: str) -> Tool | None:
                return None

            def get_tool_choices(self) -> list[str]:
                return []

            def get_exclusive_tools(self) -> list[str]:
                return []

        manager = ConcreteToolManager(tool_manager_config)

        # Assert
        assert manager._config == tool_manager_config
        assert manager._tool_evaluation_check_list == set()

    def test_does_a_tool_take_control__returns_true__when_tool_takes_control(
        self, tool_manager_config: ToolManagerConfig
    ) -> None:
        """
        Purpose: Verify does_a_tool_take_control identifies tools that take control.
        Why this matters: Some tools need exclusive control of the conversation flow.
        Setup summary: Mock tool that takes control, call method, verify True.
        """

        # Arrange
        class ConcreteToolManager(BaseToolManager):
            def get_tool_by_name(self, name: str) -> Tool | None:
                mock_tool = Mock(spec=Tool)
                mock_tool.takes_control = Mock(return_value=True)
                return mock_tool

            def get_tool_choices(self) -> list[str]:
                return []

            def get_exclusive_tools(self) -> list[str]:
                return []

        manager = ConcreteToolManager(tool_manager_config)
        tool_calls = [
            LanguageModelFunction(id="1", name="control_tool", arguments="{}")
        ]

        # Act
        result = manager.does_a_tool_take_control(tool_calls)

        # Assert
        assert result is True

    def test_does_a_tool_take_control__returns_false__when_no_tool_takes_control(
        self, tool_manager_config: ToolManagerConfig
    ) -> None:
        """
        Purpose: Verify does_a_tool_take_control returns False when no tools take control.
        Why this matters: Agent should continue normal flow when tools don't take control.
        Setup summary: Mock tool that doesn't take control, call method, verify False.
        """

        # Arrange
        class ConcreteToolManager(BaseToolManager):
            def get_tool_by_name(self, name: str) -> Tool | None:
                mock_tool = Mock(spec=Tool)
                mock_tool.takes_control = Mock(return_value=False)
                return mock_tool

            def get_tool_choices(self) -> list[str]:
                return []

            def get_exclusive_tools(self) -> list[str]:
                return []

        manager = ConcreteToolManager(tool_manager_config)
        tool_calls = [LanguageModelFunction(id="1", name="normal_tool", arguments="{}")]

        # Act
        result = manager.does_a_tool_take_control(tool_calls)

        # Assert
        assert result is False

    def test_filter_duplicate_tool_calls__removes_duplicates__with_identical_calls(
        self, tool_manager_config: ToolManagerConfig
    ) -> None:
        """
        Purpose: Verify duplicate tool calls are filtered out.
        Why this matters: Duplicate calls waste resources and can cause unexpected behavior.
        Setup summary: Create list with duplicate calls, filter, verify only unique remain.
        """

        # Arrange
        class ConcreteToolManager(BaseToolManager):
            _logger = getLogger(__name__)

            def get_tool_by_name(self, name: str) -> Tool | None:
                return None

            def get_tool_choices(self) -> list[str]:
                return []

            def get_exclusive_tools(self) -> list[str]:
                return []

        manager = ConcreteToolManager(tool_manager_config)
        tool_calls = [
            LanguageModelFunction(id="1", name="tool1", arguments='{"a": 1}'),
            LanguageModelFunction(id="2", name="tool1", arguments='{"a": 1}'),
            LanguageModelFunction(id="3", name="tool2", arguments='{"b": 2}'),
        ]

        # Act
        unique_calls = manager.filter_duplicate_tool_calls(tool_calls)

        # Assert
        assert len(unique_calls) == 2

    def test_get_evaluation_check_list__returns_list__from_set(
        self, tool_manager_config: ToolManagerConfig
    ) -> None:
        """
        Purpose: Verify get_evaluation_check_list converts internal set to list.
        Why this matters: External interface should provide list for consistent API.
        Setup summary: Add checks to internal set, get list, verify conversion.
        """

        # Arrange
        class ConcreteToolManager(BaseToolManager):
            def get_tool_by_name(self, name: str) -> Tool | None:
                return None

            def get_tool_choices(self) -> list[str]:
                return []

            def get_exclusive_tools(self) -> list[str]:
                return []

        manager = ConcreteToolManager(tool_manager_config)
        manager._tool_evaluation_check_list.add(EvaluationMetricName.CONTEXT_RELEVANCY)
        manager._tool_evaluation_check_list.add(EvaluationMetricName.ANSWER_RELEVANCY)

        # Act
        result = manager.get_evaluation_check_list()

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert EvaluationMetricName.CONTEXT_RELEVANCY in result
        assert EvaluationMetricName.ANSWER_RELEVANCY in result


# ========== ToolManager Tests ==========


class TestToolManager:
    """Test suite for ToolManager concrete implementation."""

    def test_init__initializes_tools__with_empty_config(
        self,
        mock_logger: Logger,
        tool_manager_config: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify ToolManager initializes successfully with empty tool configuration.
        Why this matters: Manager should work even without tools configured.
        Setup summary: Create manager with empty config, verify initialization.
        """
        # Arrange & Act
        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ):
            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        # Assert
        assert manager._config == tool_manager_config
        assert manager._tools == []
        assert manager._tool_choices == []
        assert manager._disabled_tools == []

    def test_init__filters_disabled_tools__with_disabled_list(
        self,
        mock_logger: Logger,
        tool_manager_config_with_tools: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
        InternalSearchTool_class: type[Tool],
    ) -> None:
        """
        Purpose: Verify ToolManager excludes tools that are in the disabled list.
        Why this matters: Users should be able to disable specific tools per request.
        Setup summary: Create manager with disabled tool, verify tool is not loaded.
        """
        # Arrange
        mock_chat_event.payload.disabled_tools = ["InternalSearchTool"]

        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ) as mock_factory:
            mock_tool = Mock(spec=Tool)
            mock_tool.name = "InternalSearchTool"
            mock_tool.is_enabled = Mock(return_value=True)
            mock_tool.is_exclusive = Mock(return_value=False)
            mock_factory.return_value = mock_tool

            # Act
            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config_with_tools,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        # Assert
        assert "InternalSearchTool" in manager._disabled_tools
        assert len(manager._tools) == 0

    def test_init__only_loads_chosen_tools__with_tool_choices(
        self,
        mock_logger: Logger,
        tool_manager_config_with_tools: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify ToolManager only loads tools that are in tool_choices.
        Why this matters: Users should be able to limit available tools per request.
        Setup summary: Set tool_choices to specific tool, verify only that tool loads.
        """
        # Arrange
        mock_chat_event.payload.tool_choices = ["InternalSearchTool"]

        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ) as mock_factory:
            mock_tool = Mock(spec=Tool)
            mock_tool.name = "InternalSearchTool"
            mock_tool.is_enabled = Mock(return_value=True)
            mock_tool.is_exclusive = Mock(return_value=False)
            mock_factory.return_value = mock_tool

            # Act
            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config_with_tools,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        # Assert
        assert len(manager._tools) == 1
        assert manager._tools[0].name == "InternalSearchTool"

    def test_get_tool_by_name__returns_tool__when_exists(
        self,
        mock_logger: Logger,
        tool_manager_config_with_tools: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify get_tool_by_name returns the correct tool when it exists.
        Why this matters: Core functionality for retrieving tools by name.
        Setup summary: Create manager with tool, call get_tool_by_name, verify return.
        """
        # Arrange
        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ) as mock_factory:
            mock_tool = Mock(spec=Tool)
            mock_tool.name = "InternalSearchTool"
            mock_tool.is_enabled = Mock(return_value=True)
            mock_tool.is_exclusive = Mock(return_value=False)
            mock_factory.return_value = mock_tool

            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config_with_tools,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        # Act
        result = manager.get_tool_by_name("InternalSearchTool")

        # Assert
        assert result is not None
        assert result.name == "InternalSearchTool"

    def test_get_tool_by_name__returns_none__when_not_exists(
        self,
        mock_logger: Logger,
        tool_manager_config: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify get_tool_by_name returns None when tool doesn't exist.
        Why this matters: Graceful handling of missing tools prevents crashes.
        Setup summary: Create manager without tools, call get_tool_by_name, verify None.
        """
        # Arrange
        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ):
            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        # Act
        result = manager.get_tool_by_name("nonexistent_tool")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_tool_call__returns_response__for_valid_tool(
        self,
        mock_logger: Logger,
        tool_manager_config_with_tools: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify execute_tool_call successfully executes a valid tool.
        Why this matters: Core functionality for executing tool calls from LLM.
        Setup summary: Mock tool with run method, execute call, verify response.
        """
        # Arrange
        expected_response = ToolCallResponse(
            id="call_1",
            name="InternalSearchTool",
            content="Test response",
        )

        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ) as mock_factory:
            mock_tool = Mock(spec=Tool)
            mock_tool.name = "InternalSearchTool"
            mock_tool.is_enabled = Mock(return_value=True)
            mock_tool.is_exclusive = Mock(return_value=False)
            mock_tool.run = AsyncMock(return_value=expected_response)
            mock_tool.evaluation_check_list = Mock(return_value=[])
            mock_factory.return_value = mock_tool

            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config_with_tools,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        tool_call = LanguageModelFunction(
            id="call_1", name="InternalSearchTool", arguments="{}"
        )

        # Act
        response = await manager.execute_tool_call(tool_call)

        # Assert
        assert response.id == "call_1"
        assert response.name == "InternalSearchTool"
        assert response.content == "Test response"

    @pytest.mark.asyncio
    async def test_execute_tool_call__returns_error__for_missing_tool(
        self,
        mock_logger: Logger,
        tool_manager_config: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify execute_tool_call returns error response for missing tool.
        Why this matters: Graceful error handling prevents agent crashes.
        Setup summary: Create manager without tools, execute call, verify error response.
        """
        # Arrange
        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ):
            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        tool_call = LanguageModelFunction(
            id="call_1", name="nonexistent_tool", arguments="{}"
        )

        # Act
        response = await manager.execute_tool_call(tool_call)

        # Assert
        assert response.id == "call_1"
        assert response.name == "nonexistent_tool"
        assert "not found" in response.error_message

    @pytest.mark.asyncio
    async def test_execute_selected_tools__limits_calls__when_exceeds_max(
        self,
        mock_logger: Logger,
        tool_manager_config: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify execute_selected_tools limits tool calls to max_tool_calls.
        Why this matters: Prevents resource exhaustion from excessive tool calls.
        Setup summary: Create many tool calls exceeding max, verify only max are executed.
        """
        # Arrange
        config = ToolManagerConfig(tools=[], max_tool_calls=2)

        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ):
            manager = ToolManager(
                logger=mock_logger,
                config=config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        tool_calls = [
            LanguageModelFunction(id=f"call_{i}", name="tool", arguments="{}")
            for i in range(5)
        ]

        # Act
        with patch.object(manager, "execute_tool_call", new=AsyncMock()) as mock_exec:
            mock_exec.return_value = ToolCallResponse(
                id="test", name="tool", content="response"
            )
            responses = await manager.execute_selected_tools(tool_calls)

        # Assert
        assert len(responses) == 2

    def test_get_tool_definitions__returns_descriptions__for_all_tools(
        self,
        mock_logger: Logger,
        tool_manager_config_with_tools: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify get_tool_definitions returns descriptions for all loaded tools.
        Why this matters: LLM needs tool descriptions to know what tools are available.
        Setup summary: Create manager with tools, get definitions, verify list.
        """
        # Arrange
        mock_description = Mock(spec=LanguageModelToolDescription)

        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ) as mock_factory:
            mock_tool = Mock(spec=Tool)
            mock_tool.name = "InternalSearchTool"
            mock_tool.is_enabled = Mock(return_value=True)
            mock_tool.is_exclusive = Mock(return_value=False)
            mock_tool.tool_description = Mock(return_value=mock_description)
            mock_factory.return_value = mock_tool

            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config_with_tools,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        # Act
        definitions = manager.get_tool_definitions()

        # Assert
        assert len(definitions) == 1
        assert definitions[0] == mock_description

    def test_add_forced_tool__adds_to_choices__when_tool_exists(
        self,
        mock_logger: Logger,
        tool_manager_config_with_tools: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify add_forced_tool adds tool name to tool_choices.
        Why this matters: Allows dynamic forcing of tool selection during execution.
        Setup summary: Create manager with tool, add forced tool, verify in choices.
        """
        # Arrange
        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ) as mock_factory:
            mock_tool = Mock(spec=Tool)
            mock_tool.name = "InternalSearchTool"
            mock_tool.is_enabled = Mock(return_value=True)
            mock_tool.is_exclusive = Mock(return_value=False)
            mock_factory.return_value = mock_tool

            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config_with_tools,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        # Act
        manager.add_forced_tool("InternalSearchTool")

        # Assert
        assert "InternalSearchTool" in manager._tool_choices

    def test_add_forced_tool__raises_error__when_tool_not_found(
        self,
        mock_logger: Logger,
        tool_manager_config: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify add_forced_tool raises ValueError when tool doesn't exist.
        Why this matters: Clear error messages help identify configuration issues.
        Setup summary: Create manager without tools, try to add forced tool, verify error.
        """
        # Arrange
        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ):
            manager = ToolManager(
                logger=mock_logger,
                config=tool_manager_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
            )

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            manager.add_forced_tool("nonexistent_tool")


# ========== ResponsesApiToolManager Tests ==========


class TestResponsesApiToolManager:
    """Test suite for ResponsesApiToolManager."""

    @pytest.mark.asyncio
    async def test_build_manager__creates_instance__with_dependencies(
        self,
        mock_logger: Logger,
        tool_manager_config: ToolManagerConfig,
        mock_chat_event: ChatEvent,
        mock_tool_progress_reporter: ToolProgressReporter,
        mock_mcp_manager: MCPManager,
        mock_a2a_manager: A2AManager,
    ) -> None:
        """
        Purpose: Verify build_manager class method creates ResponsesApiToolManager instance.
        Why this matters: Factory method pattern for creating manager with dependencies.
        Setup summary: Mock dependencies, call build_manager, verify instance creation.
        """
        # Arrange
        mock_builtin_manager = Mock(spec=OpenAIBuiltInToolManager)
        mock_builtin_manager.get_all_openai_builtin_tools = AsyncMock(
            return_value=([], [])
        )

        # Act
        with patch(
            "unique_toolkit.agentic.tools.tool_manager.ToolFactory.build_tool_with_settings"
        ):
            manager = await ResponsesApiToolManager.build_manager(
                logger=mock_logger,
                config=tool_manager_config,
                event=mock_chat_event,
                tool_progress_reporter=mock_tool_progress_reporter,
                mcp_manager=mock_mcp_manager,
                a2a_manager=mock_a2a_manager,
                builtin_tool_manager=mock_builtin_manager,
            )

        # Assert
        assert isinstance(manager, ResponsesApiToolManager)
        assert manager._config == tool_manager_config

    def test_get_tool_definitions__excludes_builtin__with_tool_choices(
        self,
        mock_logger: Logger,
        tool_manager_config: ToolManagerConfig,
    ) -> None:
        """
        Purpose: Verify get_tool_definitions excludes built-in tools when tool_choices exist.
        Why this matters: OpenAI API error when forcing selection with built-in tools.
        Setup summary: Create manager with tool choices, get definitions, verify exclusion.
        """
        # Arrange
        mock_tool = Mock(spec=Tool)
        mock_description = Mock(spec=LanguageModelToolDescription)
        mock_tool.tool_description = Mock(return_value=mock_description)

        mock_tool_manager = Mock(spec=ToolManager)
        mock_tool_manager.tool_choices = Mock(return_value=["InternalSearchTool"])
        mock_tool_manager._tool_choices = ["InternalSearchTool"]
        mock_tool_manager._exclusive_tools = []
        mock_tool_manager.get_tools = Mock(return_value=[mock_tool])

        mock_builtin_tool = Mock()
        mock_builtin_tool.tool_description = Mock(
            return_value=Mock(spec=LanguageModelToolDescription)
        )

        manager = ResponsesApiToolManager(
            logger=mock_logger,
            config=tool_manager_config,
            tool_manager=mock_tool_manager,
            builtin_tools=[mock_builtin_tool],
        )

        # Act
        definitions = manager.get_tool_definitions()

        # Assert
        assert len(definitions) == 1
        assert definitions[0] == mock_description

    def test_get_tool_definitions__includes_builtin__without_tool_choices(
        self,
        mock_logger: Logger,
        tool_manager_config: ToolManagerConfig,
    ) -> None:
        """
        Purpose: Verify get_tool_definitions includes built-in tools when no tool_choices.
        Why this matters: Built-in tools should be available when not forcing selection.
        Setup summary: Create manager without tool choices, get definitions, verify inclusion.
        """
        # Arrange
        mock_tool = Mock(spec=Tool)
        mock_description = Mock(spec=LanguageModelToolDescription)
        mock_tool.tool_description = Mock(return_value=mock_description)

        mock_tool_manager = Mock(spec=ToolManager)
        mock_tool_manager.tool_choices = Mock(return_value=[])
        mock_tool_manager._tool_choices = []
        mock_tool_manager._exclusive_tools = []
        mock_tool_manager.get_tools = Mock(return_value=[mock_tool])

        mock_builtin_tool = Mock()
        mock_builtin_description = Mock(spec=LanguageModelToolDescription)
        mock_builtin_tool.tool_description = Mock(return_value=mock_builtin_description)

        manager = ResponsesApiToolManager(
            logger=mock_logger,
            config=tool_manager_config,
            tool_manager=mock_tool_manager,
            builtin_tools=[mock_builtin_tool],
        )

        # Act
        definitions = manager.get_tool_definitions()

        # Assert
        assert len(definitions) == 2
        assert mock_description in definitions
        assert mock_builtin_description in definitions
