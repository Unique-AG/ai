import logging
from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from tests.test_obj_factory import get_event_obj
from unique_toolkit.agentic.tools.a2a import SubAgentResponseWatcher
from unique_toolkit.agentic.tools.a2a.manager import A2AManager
from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
)
from unique_toolkit.agentic.tools.openai_builtin.manager import (
    OpenAIBuiltInToolManager,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig, ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_manager import (
    ResponsesApiToolManager,
    ToolManager,
    ToolManagerConfig,
    _convert_to_forced_tool,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model.schemas import LanguageModelFunction


class MockParameters(BaseModel):
    query: str = ""


class MockToolConfig(BaseToolConfig):
    """Mock configuration for test tool"""

    pass


class MockTool(Tool[MockToolConfig]):
    """Mock tool for testing"""

    name = "mock_tool"

    def __init__(self, config, event, tool_progress_reporter=None):
        super().__init__(config, event, tool_progress_reporter)

    def tool_description(self):
        from unique_toolkit.language_model.schemas import LanguageModelToolDescription

        return LanguageModelToolDescription(
            name=self.name,
            description="Mock tool for testing",
            parameters=MockParameters,
        )

    def evaluation_check_list(self):
        return []

    def get_evaluation_checks_based_on_tool_response(self, tool_response):
        return []

    async def run(self, tool_call):
        return ToolCallResponse(
            id=tool_call.id,
            name=tool_call.name,
            content="Mock response",
        )


class MockExclusiveTool(Tool[MockToolConfig]):
    """Mock exclusive tool for testing"""

    name = "exclusive_tool"

    def __init__(self, config, event, tool_progress_reporter=None):
        super().__init__(config, event, tool_progress_reporter)

    def tool_description(self):
        from unique_toolkit.language_model.schemas import LanguageModelToolDescription

        return LanguageModelToolDescription(
            name=self.name,
            description="Mock exclusive tool",
            parameters=MockParameters,
        )

    def evaluation_check_list(self):
        return []

    def get_evaluation_checks_based_on_tool_response(self, tool_response):
        return []

    async def run(self, tool_call):
        return ToolCallResponse(
            id=tool_call.id,
            name=tool_call.name,
            content="Exclusive response",
        )


class MockControlTool(Tool[MockToolConfig]):
    """Mock tool that takes control"""

    name = "control_tool"

    def __init__(self, config, event, tool_progress_reporter=None):
        super().__init__(config, event, tool_progress_reporter)

    def tool_description(self):
        from unique_toolkit.language_model.schemas import LanguageModelToolDescription

        return LanguageModelToolDescription(
            name=self.name,
            description="Mock control tool",
            parameters=MockParameters,
        )

    def takes_control(self):
        return True

    def evaluation_check_list(self):
        return []

    def get_evaluation_checks_based_on_tool_response(self, tool_response):
        return []

    async def run(self, tool_call):
        return ToolCallResponse(
            id=tool_call.id,
            name=tool_call.name,
            content="Control response",
        )


@pytest.fixture(autouse=True)
def register_mock_tools():
    """Register mock tools with ToolFactory"""
    ToolFactory.register_tool(MockTool, MockToolConfig)
    ToolFactory.register_tool(MockExclusiveTool, MockToolConfig)
    ToolFactory.register_tool(MockControlTool, MockToolConfig)
    yield
    # Cleanup not needed as registry persists across tests


@pytest.fixture
def logger():
    """Create logger fixture."""
    return logging.getLogger(__name__)


@pytest.fixture
def base_event():
    """Create base event fixture."""
    return get_event_obj(
        user_id="test_user",
        company_id="test_company",
        assistant_id="test_assistant",
        chat_id="test_chat",
    )


@pytest.fixture
def mock_chat_service():
    """Create mock chat service fixture."""
    return Mock(spec=ChatService)


@pytest.fixture
def tool_progress_reporter(mock_chat_service):
    """Create tool progress reporter fixture."""
    return ToolProgressReporter(mock_chat_service)


@pytest.fixture
def a2a_manager(logger, tool_progress_reporter):
    """Create A2A manager fixture."""
    return A2AManager(
        logger=logger,
        tool_progress_reporter=tool_progress_reporter,
        response_watcher=SubAgentResponseWatcher(),
    )


@pytest.fixture
def mcp_manager(base_event, tool_progress_reporter):
    """Create MCP manager fixture with no servers."""
    return MCPManager(
        mcp_servers=[],
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
    )


@pytest.fixture
def tool_config():
    """Create single tool configuration fixture."""
    return ToolBuildConfig(
        name="mock_tool",
        configuration=MockToolConfig(),
        display_name="Mock Tool",
        icon=ToolIcon.BOOK,
        selection_policy=ToolSelectionPolicy.BY_USER,
        is_exclusive=False,
        is_enabled=True,
    )


@pytest.fixture
def tool_manager_config(tool_config):
    """Create tool manager configuration fixture."""
    return ToolManagerConfig(
        tools=[tool_config],
        max_tool_calls=10,
    )


@pytest.mark.ai
def test_tool_manager__initializes__with_basic_config(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify ToolManager initializes correctly with basic configuration.
    Why this matters: Ensures core initialization works for completions API mode.
    Setup summary: Create ToolManager with minimal config, verify it initializes without errors.
    """
    # Arrange & Act
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Assert
    assert tool_manager is not None
    assert tool_manager._api_mode == "completions"
    assert len(tool_manager.get_tools()) > 0


@pytest.mark.ai
def test_responses_api_tool_manager__initializes__with_builtin_tools(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    mocker,
) -> None:
    """
    Purpose: Verify ResponsesApiToolManager initializes with OpenAI built-in tools.
    Why this matters: Ensures responses API mode includes built-in tools.
    Setup summary: Create ResponsesApiToolManager with mock builtin manager, verify initialization.
    """
    # Arrange
    mock_builtin_manager = mocker.Mock(spec=OpenAIBuiltInToolManager)
    mock_builtin_manager.get_all_openai_builtin_tools.return_value = []

    # Act
    tool_manager = ResponsesApiToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        builtin_tool_manager=mock_builtin_manager,
    )

    # Assert
    assert tool_manager is not None
    assert tool_manager._api_mode == "responses"
    mock_builtin_manager.get_all_openai_builtin_tools.assert_called_once()


@pytest.mark.ai
def test_tool_manager__filters_disabled_tools__from_config(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify tools marked as disabled in config are filtered out.
    Why this matters: Ensures disabled tools don't get added to available tools.
    Setup summary: Create config with disabled tool, verify it's not in tools list.
    """
    # Arrange
    disabled_tool_config = ToolBuildConfig(
        name="mock_tool",
        configuration=MockToolConfig(),
        display_name="Mock Tool",
        icon=ToolIcon.BOOK,
        selection_policy=ToolSelectionPolicy.BY_USER,
        is_exclusive=False,
        is_enabled=False,  # Disabled
    )
    config = ToolManagerConfig(tools=[disabled_tool_config], max_tool_calls=10)

    # Act
    tool_manager = ToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Assert
    tool_names = [t.name for t in tool_manager.get_tools()]
    assert "mock_tool" not in tool_names


@pytest.mark.ai
def test_tool_manager__filters_disabled_tools__from_event(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify tools in disabled_tools list from event are filtered out.
    Why this matters: Allows runtime control of tool availability.
    Setup summary: Set event.payload.disabled_tools, verify tool is filtered.
    """
    # Arrange
    base_event.payload.disabled_tools = ["mock_tool"]

    # Act
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Assert
    tool_names = [t.name for t in tool_manager.get_tools()]
    assert "mock_tool" not in tool_names


@pytest.mark.ai
def test_tool_manager__filters_by_tool_choices__when_specified(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify only tools in tool_choices are included when choices specified.
    Why this matters: Allows limiting available tools to user selection.
    Setup summary: Create multiple tools, set tool_choices to subset, verify filtering.
    """
    # Arrange
    tool_configs = [
        ToolBuildConfig(
            name="mock_tool",
            configuration=MockToolConfig(),
            display_name="Mock Tool",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        ),
        ToolBuildConfig(
            name="control_tool",
            configuration=MockToolConfig(),
            display_name="Control Tool",
            icon=ToolIcon.ANALYTICS,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        ),
    ]
    config = ToolManagerConfig(tools=tool_configs, max_tool_calls=10)
    base_event.payload.tool_choices = ["mock_tool"]

    # Act
    tool_manager = ToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Assert
    tool_names = [t.name for t in tool_manager.get_tools()]
    assert "mock_tool" in tool_names
    assert "control_tool" not in tool_names
    assert len(tool_names) == 1


@pytest.mark.ai
def test_tool_manager__uses_exclusive_tool__when_in_tool_choices(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify exclusive tool overrides all others when in tool_choices.
    Why this matters: Ensures exclusive tools work as intended for specialized tasks.
    Setup summary: Create exclusive and regular tools, select exclusive, verify only it exists.
    """
    # Arrange
    tool_configs = [
        ToolBuildConfig(
            name="mock_tool",
            configuration=MockToolConfig(),
            display_name="Mock Tool",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        ),
        ToolBuildConfig(
            name="exclusive_tool",
            configuration=MockToolConfig(),
            display_name="Exclusive Tool",
            icon=ToolIcon.ANALYTICS,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=True,
            is_enabled=True,
        ),
    ]
    config = ToolManagerConfig(tools=tool_configs, max_tool_calls=10)
    base_event.payload.tool_choices = ["exclusive_tool"]

    # Act
    tool_manager = ToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Assert
    tools = tool_manager.get_tools()
    assert len(tools) == 1
    assert tools[0].name == "exclusive_tool"


@pytest.mark.ai
def test_tool_manager__excludes_exclusive_tool__when_not_in_choices(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify exclusive tools are excluded when not explicitly chosen.
    Why this matters: Exclusive tools should only be available when explicitly selected.
    Setup summary: Create exclusive tool without selecting it, verify it's excluded.
    """
    # Arrange
    tool_configs = [
        ToolBuildConfig(
            name="mock_tool",
            configuration=MockToolConfig(),
            display_name="Mock Tool",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        ),
        ToolBuildConfig(
            name="exclusive_tool",
            configuration=MockToolConfig(),
            display_name="Exclusive Tool",
            icon=ToolIcon.ANALYTICS,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=True,
            is_enabled=True,
        ),
    ]
    config = ToolManagerConfig(tools=tool_configs, max_tool_calls=10)

    # Act
    tool_manager = ToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Assert
    tool_names = [t.name for t in tool_manager.get_tools()]
    assert "exclusive_tool" not in tool_names
    assert "mock_tool" in tool_names


@pytest.mark.ai
def test_tool_manager__get_tool_by_name__returns_tool(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_tool_by_name returns correct tool when it exists.
    Why this matters: Core retrieval functionality for tool execution.
    Setup summary: Create tool manager, retrieve tool by name, verify it matches.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    tool = tool_manager.get_tool_by_name("mock_tool")

    # Assert
    assert tool is not None
    assert tool.name == "mock_tool"
    assert isinstance(tool, Tool)


@pytest.mark.ai
def test_tool_manager__get_tool_by_name__returns_none_for_missing(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_tool_by_name returns None for non-existent tools.
    Why this matters: Proper error handling for invalid tool names.
    Setup summary: Create tool manager, request non-existent tool, verify None returned.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    tool = tool_manager.get_tool_by_name("non_existent_tool")

    # Assert
    assert tool is None


@pytest.mark.ai
def test_tool_manager__get_tools__returns_copy(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_tools returns a copy, not original list.
    Why this matters: Prevents external modification of internal tool list.
    Setup summary: Get tools list twice, verify they're different objects.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    tools1 = tool_manager.get_tools()
    tools2 = tool_manager.get_tools()

    # Assert
    assert tools1 == tools2  # Equal content
    assert tools1 is not tools2  # Different objects


@pytest.mark.ai
def test_tool_manager__get_tool_choices__returns_copy(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_tool_choices returns a copy, not original list.
    Why this matters: Prevents external modification of internal choices list.
    Setup summary: Get choices twice, verify they're different objects.
    """
    # Arrange
    base_event.payload.tool_choices = ["mock_tool"]
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    choices1 = tool_manager.get_tool_choices()
    choices2 = tool_manager.get_tool_choices()

    # Assert
    assert choices1 == choices2
    assert choices1 is not choices2


@pytest.mark.ai
def test_tool_manager__get_exclusive_tools__returns_exclusive_names(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_exclusive_tools returns names of exclusive tools.
    Why this matters: Allows checking which tools are exclusive for special handling.
    Setup summary: Create exclusive tool, verify it appears in exclusive tools list.
    """
    # Arrange
    tool_configs = [
        ToolBuildConfig(
            name="exclusive_tool",
            configuration=MockToolConfig(),
            display_name="Exclusive Tool",
            icon=ToolIcon.ANALYTICS,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=True,
            is_enabled=True,
        ),
    ]
    config = ToolManagerConfig(tools=tool_configs, max_tool_calls=10)

    tool_manager = ToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    exclusive_tools = tool_manager.get_exclusive_tools()

    # Assert
    assert "exclusive_tool" in exclusive_tools


@pytest.mark.ai
def test_tool_manager__get_tool_definitions__returns_descriptions(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_tool_definitions returns tool descriptions for LLM.
    Why this matters: Provides tool schemas to language model for tool calling.
    Setup summary: Create tool manager, get definitions, verify structure.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    definitions = tool_manager.get_tool_definitions()

    # Assert
    assert len(definitions) > 0
    definition = definitions[0]
    assert hasattr(definition, "name")
    assert hasattr(definition, "description")


@pytest.mark.ai
def test_tool_manager__get_forced_tools__returns_forced_tool_params(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_forced_tools returns proper format for forced tool calls.
    Why this matters: Enables forcing specific tools in LLM requests.
    Setup summary: Set tool_choices, verify forced tools returned in correct format.
    """
    # Arrange
    base_event.payload.tool_choices = ["mock_tool"]
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    forced_tools = tool_manager.get_forced_tools()

    # Assert
    assert len(forced_tools) == 1
    forced_tool = forced_tools[0]
    assert forced_tool["type"] == "function"
    assert forced_tool["function"]["name"] == "mock_tool"


@pytest.mark.ai
def test_tool_manager__get_tool_prompts__returns_prompt_info(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_tool_prompts returns prompt information for all tools.
    Why this matters: Provides system/user prompts for tool usage instructions.
    Setup summary: Create tool manager, get prompts, verify structure.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    prompts = tool_manager.get_tool_prompts()

    # Assert
    assert len(prompts) > 0
    prompt = prompts[0]
    assert hasattr(prompt, "name")
    assert hasattr(prompt, "tool_system_prompt")


@pytest.mark.ai
def test_tool_manager__does_a_tool_take_control__returns_true_for_control_tool(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify does_a_tool_take_control detects tools that take control.
    Why this matters: Some tools need exclusive conversation control.
    Setup summary: Create control tool, make tool call, verify detection.
    """
    # Arrange
    tool_configs = [
        ToolBuildConfig(
            name="control_tool",
            configuration=MockToolConfig(),
            display_name="Control Tool",
            icon=ToolIcon.ANALYTICS,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        ),
    ]
    config = ToolManagerConfig(tools=tool_configs, max_tool_calls=10)
    tool_manager = ToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="control_tool",
            arguments={"query": "test"},
        )
    ]

    # Act
    takes_control = tool_manager.does_a_tool_take_control(tool_calls)

    # Assert
    assert takes_control is True


@pytest.mark.ai
def test_tool_manager__does_a_tool_take_control__returns_false_for_normal_tool(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify does_a_tool_take_control returns False for normal tools.
    Why this matters: Only special tools should take control, not regular ones.
    Setup summary: Create normal tool, make tool call, verify no control taken.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="mock_tool",
            arguments={"query": "test"},
        )
    ]

    # Act
    takes_control = tool_manager.does_a_tool_take_control(tool_calls)

    # Assert
    assert takes_control is False


@pytest.mark.ai
def test_tool_manager__filter_duplicate_tool_calls__removes_duplicates(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify duplicate tool calls with same ID, name and arguments are filtered.
    Why this matters: Prevents redundant tool execution and wasted resources.
    Setup summary: Create duplicate tool calls with same values, filter them, verify only one remains.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    # Create truly duplicate calls - same ID makes them equal
    call = LanguageModelFunction(
        id="call_1",
        name="mock_tool",
        arguments={"query": "test"},
    )
    tool_calls = [call, call]  # Same object reference

    # Act
    filtered = tool_manager.filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(filtered) == 1
    assert filtered[0].name == "mock_tool"


@pytest.mark.ai
def test_tool_manager__filter_duplicate_tool_calls__keeps_different_args(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify tool calls with different arguments are not filtered.
    Why this matters: Different arguments represent different operations.
    Setup summary: Create tool calls with different args, verify both kept.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="mock_tool",
            arguments={"query": "test1"},
        ),
        LanguageModelFunction(
            id="call_2",
            name="mock_tool",
            arguments={"query": "test2"},
        ),
    ]

    # Act
    filtered = tool_manager.filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(filtered) == 2


@pytest.mark.ai
def test_tool_manager__filter_tool_calls_by_max_tool_calls_allowed__limits_to_max(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify filter_tool_calls_by_max_tool_calls_allowed limits to max_tool_calls.
    Why this matters: Prevents resource exhaustion from too many tool calls.
    Setup summary: Create 15 tool calls with max_tool_calls=10, verify only 10 returned.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id=f"call_{i}",
            name="mock_tool",
            arguments={"query": f"test{i}"},
        )
        for i in range(15)
    ]

    # Act
    filtered = tool_manager.filter_tool_calls_by_max_tool_calls_allowed(tool_calls)

    # Assert
    assert len(filtered) == 10
    # Verify first 10 are kept
    for i in range(10):
        assert filtered[i].id == f"call_{i}"


@pytest.mark.ai
def test_tool_manager__filter_tool_calls_by_max_tool_calls_allowed__keeps_all_if_under_max(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify filter_tool_calls_by_max_tool_calls_allowed keeps all when under max.
    Why this matters: Should not filter when under the limit.
    Setup summary: Create 5 tool calls with max_tool_calls=10, verify all 5 returned.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id=f"call_{i}",
            name="mock_tool",
            arguments={"query": f"test{i}"},
        )
        for i in range(5)
    ]

    # Act
    filtered = tool_manager.filter_tool_calls_by_max_tool_calls_allowed(tool_calls)

    # Assert
    assert len(filtered) == 5


@pytest.mark.ai
def test_tool_manager__filter_tool_calls_by_max_tool_calls_allowed__logs_warning_when_limiting(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    caplog,
) -> None:
    """
    Purpose: Verify filter_tool_calls_by_max_tool_calls_allowed logs warning when limiting.
    Why this matters: Users should be notified when tool calls are being limited.
    Setup summary: Create 15 tool calls with max_tool_calls=10, verify warning logged.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id=f"call_{i}",
            name="mock_tool",
            arguments={"query": f"test{i}"},
        )
        for i in range(15)
    ]

    # Act
    with caplog.at_level(logging.WARNING):
        filtered = tool_manager.filter_tool_calls_by_max_tool_calls_allowed(tool_calls)

    # Assert
    assert len(filtered) == 10
    assert "exceeds the allowed maximum" in caplog.text


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_manager__execute_tool_call__returns_response(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify execute_tool_call executes tool and returns response.
    Why this matters: Core functionality for tool execution.
    Setup summary: Create tool call, execute it, verify response structure.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_call = LanguageModelFunction(
        id="call_1",
        name="mock_tool",
        arguments={"query": "test"},
    )

    # Act
    response = await tool_manager.execute_tool_call(tool_call)

    # Assert
    assert isinstance(response, ToolCallResponse)
    assert response.id == "call_1"
    assert response.name == "mock_tool"
    assert response.successful


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_manager__execute_selected_tools__handles_missing_tool(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify execute_selected_tools handles non-existent tool gracefully.
    Why this matters: Prevents crashes from invalid tool calls.
    Setup summary: Call non-existent tool via execute_selected_tools, verify error response returned.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="non_existent_tool",
            arguments={"query": "test"},
        )
    ]

    # Act
    responses = await tool_manager.execute_selected_tools(tool_calls)

    # Assert
    assert len(responses) == 1
    response = responses[0]
    assert isinstance(response, ToolCallResponse)
    # Error handled by SafeTaskExecutor at the execute_selected_tools level
    assert "non_existent_tool" in response.name or response.error_message


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_manager__execute_selected_tools__executes_in_parallel(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify execute_selected_tools executes multiple tools concurrently.
    Why this matters: Parallel execution improves performance.
    Setup summary: Execute multiple tool calls, verify all responses returned.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id=f"call_{i}",
            name="mock_tool",
            arguments={"query": f"test{i}"},
        )
        for i in range(3)
    ]

    # Act
    responses = await tool_manager.execute_selected_tools(tool_calls)

    # Assert
    assert len(responses) == 3
    for i, response in enumerate(responses):
        assert response.id == f"call_{i}"
        assert response.successful


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_manager__execute_selected_tools__adds_debug_info(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify execute_selected_tools adds debug info to responses.
    Why this matters: Debug info helps with troubleshooting and metrics.
    Setup summary: Execute tool call, verify debug_info includes is_exclusive and is_forced.
    """
    # Arrange
    base_event.payload.tool_choices = ["mock_tool"]
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="mock_tool",
            arguments={"query": "test"},
        )
    ]

    # Act
    responses = await tool_manager.execute_selected_tools(tool_calls)

    # Assert
    assert len(responses) == 1
    assert responses[0].debug_info is not None
    assert "is_exclusive" in responses[0].debug_info
    assert "is_forced" in responses[0].debug_info
    assert responses[0].debug_info["is_forced"] is True


@pytest.mark.ai
def test_tool_manager__filter_tool_calls__filters_by_internal_type(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify filter_tool_calls filters by tool type (internal).
    Why this matters: Allows selective execution of tool types.
    Setup summary: Create tool calls, filter by internal type, verify correct filtering.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="mock_tool",
            arguments={"query": "test"},
        )
    ]

    # Act
    filtered = tool_manager.filter_tool_calls(tool_calls, ["internal"])

    # Assert
    assert len(filtered) == 1
    assert filtered[0].name == "mock_tool"


@pytest.mark.ai
def test_tool_manager__filter_tool_calls__excludes_wrong_type(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify filter_tool_calls excludes tools of unspecified types.
    Why this matters: Type filtering must be precise.
    Setup summary: Filter by mcp type with only internal tools, verify empty result.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="mock_tool",
            arguments={"query": "test"},
        )
    ]

    # Act
    filtered = tool_manager.filter_tool_calls(tool_calls, ["mcp"])

    # Assert
    assert len(filtered) == 0


@pytest.mark.ai
def test_tool_manager__add_forced_tool__adds_to_choices(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify add_forced_tool adds tool to choices list.
    Why this matters: Allows dynamic addition of forced tools.
    Setup summary: Add forced tool, verify it appears in tool_choices.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    tool_manager.add_forced_tool("mock_tool")

    # Assert
    choices = tool_manager.get_tool_choices()
    assert "mock_tool" in choices


@pytest.mark.ai
def test_tool_manager__add_forced_tool__raises_for_missing_tool(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify add_forced_tool raises ValueError for non-existent tools.
    Why this matters: Prevents adding invalid tools to forced list.
    Setup summary: Try to add non-existent tool, verify ValueError raised.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        tool_manager.add_forced_tool("non_existent_tool")
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.ai
def test_tool_manager__log_loaded_tools__logs_tool_names(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    caplog,
) -> None:
    """
    Purpose: Verify log_loaded_tools outputs tool names to log.
    Why this matters: Debugging and operational visibility.
    Setup summary: Create tool manager, call log_loaded_tools, verify log output.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    with caplog.at_level(logging.INFO):
        tool_manager.log_loaded_tools()

    # Assert
    assert "mock_tool" in caplog.text
    assert "Loaded tools" in caplog.text


@pytest.mark.ai
def test_convert_to_forced_tool__formats_completions_correctly() -> None:
    """
    Purpose: Verify _convert_to_forced_tool formats completions API correctly.
    Why this matters: Correct API format needed for OpenAI completions.
    Setup summary: Call converter with completions mode, verify structure.
    """
    # Arrange & Act
    result = _convert_to_forced_tool("test_tool", mode="completions")

    # Assert
    assert result["type"] == "function"
    assert result["function"]["name"] == "test_tool"


@pytest.mark.ai
def test_convert_to_forced_tool__formats_responses_correctly() -> None:
    """
    Purpose: Verify _convert_to_forced_tool formats responses API correctly.
    Why this matters: Correct API format needed for OpenAI responses.
    Setup summary: Call converter with responses mode, verify structure.
    """
    # Arrange & Act
    result = _convert_to_forced_tool("test_tool", mode="responses")

    # Assert
    assert result["type"] == "function"
    assert result["name"] == "test_tool"


@pytest.mark.ai
def test_convert_to_forced_tool__formats_builtin_tool_special() -> None:
    """
    Purpose: Verify _convert_to_forced_tool formats built-in tools specially.
    Why this matters: Built-in tools have different syntax in responses API.
    Setup summary: Call converter with built-in tool name, verify special format.
    """
    # Arrange & Act
    result = _convert_to_forced_tool("code_interpreter", mode="responses")

    # Assert
    assert result["type"] == "code_interpreter"
    assert "name" not in result


@pytest.mark.ai
def test_tool_manager__get_evaluation_check_list__returns_list(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify get_evaluation_check_list returns evaluation metrics list.
    Why this matters: Tracks which evaluations are needed after tool execution.
    Setup summary: Create tool manager, verify evaluation list is empty initially.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    check_list = tool_manager.get_evaluation_check_list()

    # Assert
    assert isinstance(check_list, list)


@pytest.mark.ai
def test_tool_manager__sub_agents__returns_sub_agent_list(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify sub_agents property returns list of sub-agent tools.
    Why this matters: Provides access to sub-agents for special handling.
    Setup summary: Create tool manager, verify sub_agents property exists and is list.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Act
    sub_agents = tool_manager.sub_agents

    # Assert
    assert isinstance(sub_agents, list)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_manager__execute_selected_tools__handles_exceptions(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    mocker,
) -> None:
    """
    Purpose: Verify execute_selected_tools handles tool execution exceptions gracefully.
    Why this matters: Tool failures shouldn't crash the system.
    Setup summary: Mock tool to raise exception, execute via execute_selected_tools, verify error response.
    """
    # Arrange
    tool_configs = [
        ToolBuildConfig(
            name="mock_tool",
            configuration=MockToolConfig(),
            display_name="Mock Tool",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        ),
    ]
    config = ToolManagerConfig(tools=tool_configs, max_tool_calls=10)
    tool_manager = ToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    # Mock the tool's run method to raise an exception
    mock_tool = tool_manager.get_tool_by_name("mock_tool")
    mocker.patch.object(mock_tool, "run", side_effect=RuntimeError("Tool error"))

    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="mock_tool",
            arguments={"query": "test"},
        )
    ]

    # Act
    responses = await tool_manager.execute_selected_tools(tool_calls)

    # Assert
    assert len(responses) == 1
    response = responses[0]
    assert isinstance(response, ToolCallResponse)
    assert not response.successful
    assert "Tool error" in response.error_message


@pytest.mark.ai
def test_responses_api_tool_manager__get_tool_by_name__can_return_builtin(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    mocker,
) -> None:
    """
    Purpose: Verify ResponsesApiToolManager can retrieve built-in tools.
    Why this matters: Responses API supports OpenAI built-in tools.
    Setup summary: Create mock built-in tool, retrieve it, verify type.
    """
    # Arrange
    mock_builtin_tool = mocker.Mock(spec=OpenAIBuiltInTool)
    mock_builtin_tool.name = "code_interpreter"
    mock_builtin_tool.is_enabled.return_value = True
    mock_builtin_tool.is_exclusive.return_value = False

    mock_builtin_manager = mocker.Mock(spec=OpenAIBuiltInToolManager)
    mock_builtin_manager.get_all_openai_builtin_tools.return_value = [mock_builtin_tool]

    tool_manager = ResponsesApiToolManager(
        logger=logger,
        config=ToolManagerConfig(tools=[], max_tool_calls=10),
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        builtin_tool_manager=mock_builtin_manager,
    )

    # Act
    tool = tool_manager.get_tool_by_name("code_interpreter")

    # Assert
    assert tool is not None
    assert tool.name == "code_interpreter"


@pytest.mark.ai
def test_responses_api_tool_manager__filter_tool_calls__filters_builtin(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    mocker,
) -> None:
    """
    Purpose: Verify ResponsesApiToolManager filters built-in tool calls.
    Why this matters: Type filtering must include built-in tools.
    Setup summary: Create built-in tool call, filter by openai_builtin type, verify included.
    """
    # Arrange
    mock_builtin_tool = mocker.Mock(spec=OpenAIBuiltInTool)
    mock_builtin_tool.name = "code_interpreter"
    mock_builtin_tool.is_enabled.return_value = True
    mock_builtin_tool.is_exclusive.return_value = False

    mock_builtin_manager = mocker.Mock(spec=OpenAIBuiltInToolManager)
    mock_builtin_manager.get_all_openai_builtin_tools.return_value = [mock_builtin_tool]

    tool_manager = ResponsesApiToolManager(
        logger=logger,
        config=ToolManagerConfig(tools=[], max_tool_calls=10),
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        builtin_tool_manager=mock_builtin_manager,
    )

    tool_calls = [
        LanguageModelFunction(
            id="call_1",
            name="code_interpreter",
            arguments={},
        )
    ]

    # Act
    filtered = tool_manager.filter_tool_calls(tool_calls, ["openai_builtin"])

    # Assert
    assert len(filtered) == 1
    assert filtered[0].name == "code_interpreter"


@pytest.mark.ai
def test_responses_api_tool_manager__get_forced_tools__formats_builtin_special(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    mocker,
) -> None:
    """
    Purpose: Verify ResponsesApiToolManager formats built-in forced tools correctly.
    Why this matters: Built-in tools require special format in responses API.
    Setup summary: Force built-in tool, get forced tools, verify format.
    """
    # Arrange
    mock_builtin_tool = mocker.Mock(spec=OpenAIBuiltInTool)
    mock_builtin_tool.name = "code_interpreter"
    mock_builtin_tool.is_enabled.return_value = True
    mock_builtin_tool.is_exclusive.return_value = False

    mock_builtin_manager = mocker.Mock(spec=OpenAIBuiltInToolManager)
    mock_builtin_manager.get_all_openai_builtin_tools.return_value = [mock_builtin_tool]

    base_event.payload.tool_choices = ["code_interpreter"]

    tool_manager = ResponsesApiToolManager(
        logger=logger,
        config=ToolManagerConfig(tools=[], max_tool_calls=10),
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        builtin_tool_manager=mock_builtin_manager,
    )

    # Act
    forced_tools = tool_manager.get_forced_tools()

    # Assert
    assert len(forced_tools) == 1
    assert forced_tools[0]["type"] == "code_interpreter"


@pytest.mark.ai
def test_tool_manager__filter_tool_calls_by_max_tool_calls_allowed__returns_all_when_equal_to_max(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
) -> None:
    """
    Purpose: Verify filter_tool_calls_by_max_tool_calls_allowed returns all when exactly at max.
    Why this matters: Edge case where count equals max should return all tool calls.
    Setup summary: Create exactly 10 tool calls with max_tool_calls=10, verify all 10 returned.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id=f"call_{i}",
            name="mock_tool",
            arguments={"query": f"test{i}"},
        )
        for i in range(10)
    ]

    # Act
    filtered = tool_manager.filter_tool_calls_by_max_tool_calls_allowed(tool_calls)

    # Assert
    assert len(filtered) == 10
    # Verify all are kept
    for i in range(10):
        assert filtered[i].id == f"call_{i}"


@pytest.mark.ai
def test_tool_manager__filter_tool_calls_by_max_tool_calls_allowed__does_not_log_when_at_max(
    logger,
    tool_manager_config,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    caplog,
) -> None:
    """
    Purpose: Verify filter_tool_calls_by_max_tool_calls_allowed does not log when at max.
    Why this matters: Warning should only be logged when exceeding, not when at limit.
    Setup summary: Create exactly 10 tool calls with max_tool_calls=10, verify no warning logged.
    """
    # Arrange
    tool_manager = ToolManager(
        logger=logger,
        config=tool_manager_config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id=f"call_{i}",
            name="mock_tool",
            arguments={"query": f"test{i}"},
        )
        for i in range(10)
    ]

    # Act
    with caplog.at_level(logging.WARNING):
        filtered = tool_manager.filter_tool_calls_by_max_tool_calls_allowed(tool_calls)

    # Assert
    assert len(filtered) == 10
    assert "exceeds the allowed maximum" not in caplog.text


@pytest.mark.ai
def test_responses_api_tool_manager__filter_tool_calls_by_max_tool_calls_allowed__limits_to_max(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    mocker,
    caplog,
) -> None:
    """
    Purpose: Verify ResponsesApiToolManager filter_tool_calls_by_max_tool_calls_allowed limits to max.
    Why this matters: Ensures the method works for ResponsesApiToolManager as well.
    Setup summary: Create ResponsesApiToolManager with 15 tool calls and max=10, verify only 10 returned.
    """
    # Arrange
    mock_builtin_manager = mocker.Mock(spec=OpenAIBuiltInToolManager)
    mock_builtin_manager.get_all_openai_builtin_tools.return_value = []

    tool_configs = [
        ToolBuildConfig(
            name="mock_tool",
            configuration=MockToolConfig(),
            display_name="Mock Tool",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        ),
    ]
    config = ToolManagerConfig(tools=tool_configs, max_tool_calls=10)
    
    tool_manager = ResponsesApiToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        builtin_tool_manager=mock_builtin_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id=f"call_{i}",
            name="mock_tool",
            arguments={"query": f"test{i}"},
        )
        for i in range(15)
    ]

    # Act
    with caplog.at_level(logging.WARNING):
        filtered = tool_manager.filter_tool_calls_by_max_tool_calls_allowed(tool_calls)

    # Assert
    assert len(filtered) == 10
    assert "exceeds the allowed maximum" in caplog.text
    # Verify first 10 are kept
    for i in range(10):
        assert filtered[i].id == f"call_{i}"


@pytest.mark.ai
def test_responses_api_tool_manager__filter_tool_calls_by_max_tool_calls_allowed__keeps_all_if_under_max(
    logger,
    base_event,
    tool_progress_reporter,
    mcp_manager,
    a2a_manager,
    mocker,
) -> None:
    """
    Purpose: Verify ResponsesApiToolManager filter_tool_calls_by_max_tool_calls_allowed keeps all when under max.
    Why this matters: Ensures the method works correctly for ResponsesApiToolManager when under limit.
    Setup summary: Create ResponsesApiToolManager with 5 tool calls and max=10, verify all 5 returned.
    """
    # Arrange
    mock_builtin_manager = mocker.Mock(spec=OpenAIBuiltInToolManager)
    mock_builtin_manager.get_all_openai_builtin_tools.return_value = []

    tool_configs = [
        ToolBuildConfig(
            name="mock_tool",
            configuration=MockToolConfig(),
            display_name="Mock Tool",
            icon=ToolIcon.BOOK,
            selection_policy=ToolSelectionPolicy.BY_USER,
            is_exclusive=False,
            is_enabled=True,
        ),
    ]
    config = ToolManagerConfig(tools=tool_configs, max_tool_calls=10)
    
    tool_manager = ResponsesApiToolManager(
        logger=logger,
        config=config,
        event=base_event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        builtin_tool_manager=mock_builtin_manager,
    )
    tool_calls = [
        LanguageModelFunction(
            id=f"call_{i}",
            name="mock_tool",
            arguments={"query": f"test{i}"},
        )
        for i in range(5)
    ]

    # Act
    filtered = tool_manager.filter_tool_calls_by_max_tool_calls_allowed(tool_calls)

    # Assert
    assert len(filtered) == 5
