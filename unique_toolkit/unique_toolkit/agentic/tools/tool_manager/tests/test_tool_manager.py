from typing import Any

import pytest

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.agent_chunks_hanlder import AgentChunksHandler
from unique_toolkit.agentic.tools.config import ToolBuildConfig, ToolSelectionPolicy
from unique_toolkit.agentic.tools.schemas import (
    BaseToolConfig,
    ToolCallResponse,
    ToolPrompts,
)
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_manager.tool_manager import (
    ToolManager,
    ToolManagerConfig,
    _compute_available_tools,
    _get_forced_tool_definition,
)
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolDescription,
)

# ==================== Mock Tool for Testing ====================


class MockToolConfig(BaseToolConfig):
    """Empty config for testing."""
    pass


class MockTool(Tool[MockToolConfig]):
    """Mock tool for testing that inherits from actual Tool class."""

    def __init__(
        self,
        name: str,
        is_enabled: bool = True,
        is_exclusive: bool = False,
        event: ChatEvent | None = None,
    ) -> None:
        # Set name first (required by parent __init__)
        self.name = name
        
        # Create minimal config
        config = MockToolConfig()
        
        # Pre-create settings to bypass ToolFactory validation in parent __init__
        # Use model_construct to bypass Pydantic validation
        self.settings = ToolBuildConfig.model_construct(
            name=name,
            configuration=config,
            is_enabled=is_enabled,
            is_exclusive=is_exclusive,
        )
        
        # Create minimal event if not provided
        if event is None:
            event = ChatEvent(
                id="test_event_id",
                event="chat.event",
                user_id="test_user",
                company_id="test_company",
                payload=ChatEventPayload(
                    name="test",
                    description="test",
                    configuration={},
                    chat_id="test_chat",
                    assistant_id="test_assistant",
                    user_message=ChatEventUserMessage(
                        id="msg_1",
                        text="test",
                        original_text="test",
                        created_at="2024-01-01",
                        language="en",
                    ),
                    assistant_message=ChatEventAssistantMessage(
                        id="msg_2",
                        created_at="2024-01-01",
                    ),
                ),
            )
        
        # Call Tool.__init__ but skip the settings creation since we already did it
        self.config = config
        module_name = "test_module"
        from logging import getLogger
        self.logger = getLogger(f"{module_name}.{__name__}")
        self.debug_info: dict = {}
        
        # Set deprecated properties
        self._event = event
        self._tool_progress_reporter = None
        
        from unique_toolkit.chat.service import ChatService
        from unique_toolkit.language_model.service import LanguageModelService
        self._chat_service = ChatService(event)
        self._language_model_service = LanguageModelService(event)

    def tool_description(self) -> LanguageModelToolDescription:
        """Return mock tool description."""
        return LanguageModelToolDescription(
            name=self.name,
            description=f"Description for {self.name}",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        """Return dummy successful response."""
        return ToolCallResponse(
            id=tool_call.id,
            name=tool_call.name,
            content=f"Mock response from {self.name}",
        )

    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
        agent_chunks_handler: AgentChunksHandler,
    ) -> LanguageModelMessage:
        """Required abstract method - return dummy message."""
        return LanguageModelMessage(
            role="tool",
            content=tool_response.content,
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        """Required abstract method - return empty list."""
        return []

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        """Required abstract method - return empty list."""
        return []


class SimpleMockTool:
    """Simple mock tool for Layer 1 tests (testing _compute_available_tools)."""

    def __init__(
        self,
        name: str,
        is_enabled: bool = True,
        is_exclusive: bool = False,
    ) -> None:
        self.name = name
        self._is_enabled = is_enabled
        self._is_exclusive = is_exclusive

    def is_enabled(self) -> bool:
        return self._is_enabled

    def is_exclusive(self) -> bool:
        return self._is_exclusive

    def display_name(self) -> str:
        return self.name

    def icon(self) -> str:
        return "icon"

    def selection_policy(self) -> ToolSelectionPolicy:
        return ToolSelectionPolicy.BY_USER


class MockBuiltInTool:
    """Mock built-in tool implementing OpenAIBuiltInTool protocol for testing."""

    def __init__(
        self,
        name: str,
        is_enabled: bool = True,
        is_exclusive: bool = False,
    ) -> None:
        self.name = name
        self._is_enabled = is_enabled
        self._is_exclusive = is_exclusive

    def is_enabled(self) -> bool:
        return self._is_enabled

    def is_exclusive(self) -> bool:
        return self._is_exclusive

    def display_name(self) -> str:
        return f"Builtin {self.name}"

    def icon(self) -> str:
        return "builtin-icon"

    def selection_policy(self) -> ToolSelectionPolicy:
        return ToolSelectionPolicy.BY_USER

    def get_tool_prompts(self) -> ToolPrompts:
        """Return mock tool prompts."""
        return ToolPrompts(
            name=self.name,
            display_name=self.display_name(),
            tool_description=f"Builtin description for {self.name}",
            tool_system_prompt="",
            tool_format_information_for_system_prompt="",
            input_model={},
            tool_user_prompt="",
            tool_format_information_for_user_prompt="",
        )

    def tool_description(self) -> dict[str, Any]:
        """Return mock builtin tool description (different format than regular tools)."""
        return {
            "type": self.name,
            "container": "auto",
        }


# ==================== Fixtures ====================

# Fixtures for Layer 1 tests (_compute_available_tools)
@pytest.fixture
def enabled_tool() -> SimpleMockTool:
    """Create an enabled tool for testing."""
    return SimpleMockTool(name="search_tool", is_enabled=True, is_exclusive=False)


@pytest.fixture
def disabled_tool() -> SimpleMockTool:
    """Create a disabled tool for testing."""
    return SimpleMockTool(name="disabled_tool", is_enabled=False, is_exclusive=False)


@pytest.fixture
def exclusive_tool() -> SimpleMockTool:
    """Create an exclusive tool for testing."""
    return SimpleMockTool(name="exclusive_tool", is_enabled=True, is_exclusive=True)


@pytest.fixture
def standard_tools() -> list[SimpleMockTool]:
    """Create a list of standard enabled tools."""
    return [
        SimpleMockTool(name="search", is_enabled=True, is_exclusive=False),
        SimpleMockTool(name="weather", is_enabled=True, is_exclusive=False),
        SimpleMockTool(name="calculator", is_enabled=True, is_exclusive=False),
    ]


# ==================== Tests for _compute_available_tools ====================


@pytest.mark.ai
def test_compute_available_tools__returns_empty_list__when_no_tools_provided() -> None:
    """
    Purpose: Verify function handles empty tools list correctly.
    Why this matters: Edge case handling prevents runtime errors.
    Setup summary: Pass empty tools list, assert empty result.
    """
    # Arrange
    tools: list[MockTool] = []
    tool_choices: list[str] = []
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert result == []


@pytest.mark.ai
def test_compute_available_tools__returns_all_enabled_tools__when_no_filters(
    standard_tools: list[MockTool],
) -> None:
    """
    Purpose: Verify function returns all enabled tools when no filters applied.
    Why this matters: Default behavior should include all available tools.
    Setup summary: Provide enabled tools with no filters, assert all returned.
    """
    # Arrange
    tool_choices: list[str] = []
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(standard_tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 3
    assert result == standard_tools


@pytest.mark.ai
def test_compute_available_tools__excludes_disabled_tools__from_result(
    standard_tools: list[MockTool],
) -> None:
    """
    Purpose: Verify function filters out tools in disabled_tools list.
    Why this matters: Respects explicit tool disabling configuration.
    Setup summary: Mark one tool as disabled, assert it's excluded from result.
    """
    # Arrange
    tool_choices: list[str] = []
    disabled_tools: list[str] = ["weather"]

    # Act
    result = _compute_available_tools(standard_tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 2
    assert all(t.name != "weather" for t in result)
    assert any(t.name == "search" for t in result)
    assert any(t.name == "calculator" for t in result)


@pytest.mark.ai
def test_compute_available_tools__excludes_tools_with_is_enabled_false() -> None:
    """
    Purpose: Verify function filters out tools where is_enabled() returns False.
    Why this matters: Respects tool-level enable/disable state.
    Setup summary: Create mix of enabled/disabled tools, assert only enabled returned.
    """
    # Arrange
    tools = [
        MockTool(name="enabled1", is_enabled=True),
        MockTool(name="disabled1", is_enabled=False),
        MockTool(name="enabled2", is_enabled=True),
        MockTool(name="disabled2", is_enabled=False),
    ]
    tool_choices: list[str] = []
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 2
    assert all(t.is_enabled() for t in result)
    assert {t.name for t in result} == {"enabled1", "enabled2"}


@pytest.mark.ai
def test_compute_available_tools__includes_only_tool_choices__when_specified(
    standard_tools: list[MockTool],
) -> None:
    """
    Purpose: Verify function filters to only include tools in tool_choices.
    Why this matters: Allows selective tool enabling for specific use cases.
    Setup summary: Provide tool_choices list, assert only those tools returned.
    """
    # Arrange
    tool_choices: list[str] = ["search", "calculator"]
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(standard_tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 2
    assert all(t.name in tool_choices for t in result)
    assert {t.name for t in result} == {"search", "calculator"}


@pytest.mark.ai
def test_compute_available_tools__tool_choices_override_default_inclusion(
    standard_tools: list[MockTool],
) -> None:
    """
    Purpose: Verify tool_choices acts as whitelist, excluding non-specified tools.
    Why this matters: Ensures explicit tool selection works correctly.
    Setup summary: Specify single tool choice, verify others excluded.
    """
    # Arrange
    tool_choices: list[str] = ["weather"]
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(standard_tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 1
    assert result[0].name == "weather"


@pytest.mark.ai
def test_compute_available_tools__disabled_tools_override_tool_choices() -> None:
    """
    Purpose: Verify disabled_tools takes precedence over tool_choices.
    Why this matters: Explicit disabling should override explicit enabling.
    Setup summary: Add tool to both tool_choices and disabled_tools, assert excluded.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True),
        MockTool(name="weather", is_enabled=True),
    ]
    tool_choices: list[str] = ["search", "weather"]
    disabled_tools: list[str] = ["weather"]

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 1
    assert result[0].name == "search"


@pytest.mark.ai
def test_compute_available_tools__excludes_exclusive_tools__when_no_tool_choices() -> None:
    """
    Purpose: Verify exclusive tools are excluded when tool_choices is empty.
    Why this matters: Exclusive tools should only be available when explicitly chosen.
    Setup summary: Include exclusive tool without tool_choices, assert it's excluded.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True, is_exclusive=False),
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
        MockTool(name="weather", is_enabled=True, is_exclusive=False),
    ]
    tool_choices: list[str] = []
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 2
    assert all(not t.is_exclusive() for t in result)
    assert {t.name for t in result} == {"search", "weather"}


@pytest.mark.ai
def test_compute_available_tools__returns_only_exclusive_tool__when_explicitly_chosen() -> None:
    """
    Purpose: Verify exclusive tool overrides all others when explicitly chosen.
    Why this matters: Exclusive tools should take full control when selected.
    Setup summary: Choose exclusive tool in tool_choices, assert only it's returned.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True, is_exclusive=False),
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
        MockTool(name="weather", is_enabled=True, is_exclusive=False),
    ]
    tool_choices: list[str] = ["exclusive", "search"]
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 1
    assert result[0].name == "exclusive"
    assert result[0].is_exclusive()


@pytest.mark.ai
def test_compute_available_tools__exclusive_tool_breaks_iteration__immediately() -> None:
    """
    Purpose: Verify exclusive tool stops processing remaining tools.
    Why this matters: Performance optimization and correct exclusive behavior.
    Setup summary: Place exclusive tool in middle of list, verify later tools not processed.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True, is_exclusive=False),
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
        MockTool(name="tool2", is_enabled=True, is_exclusive=False),
        MockTool(name="tool3", is_enabled=True, is_exclusive=False),
    ]
    tool_choices: list[str] = ["tool1", "exclusive", "tool2", "tool3"]
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 1
    assert result[0].name == "exclusive"


@pytest.mark.ai
def test_compute_available_tools__exclusive_tool_without_tool_choice__gets_skipped() -> None:
    """
    Purpose: Verify exclusive tool is skipped when not in tool_choices but tool_choices exist.
    Why this matters: Exclusive tools should only be included when explicitly chosen.
    Setup summary: Provide tool_choices without exclusive tool, assert it's excluded.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True, is_exclusive=False),
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
        MockTool(name="weather", is_enabled=True, is_exclusive=False),
    ]
    tool_choices: list[str] = ["search", "weather"]
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 2
    assert all(t.name != "exclusive" for t in result)
    assert {t.name for t in result} == {"search", "weather"}


@pytest.mark.ai
def test_compute_available_tools__multiple_filters_combine_correctly() -> None:
    """
    Purpose: Verify multiple filter conditions work together properly.
    Why this matters: Real-world usage involves multiple filtering rules.
    Setup summary: Apply is_enabled, disabled_tools, and tool_choices filters together.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True, is_exclusive=False),
        MockTool(name="tool2", is_enabled=False, is_exclusive=False),
        MockTool(name="tool3", is_enabled=True, is_exclusive=False),
        MockTool(name="tool4", is_enabled=True, is_exclusive=False),
        MockTool(name="tool5", is_enabled=True, is_exclusive=False),
    ]
    tool_choices: list[str] = ["tool1", "tool3", "tool4"]
    disabled_tools: list[str] = ["tool4"]

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 2
    assert {t.name for t in result} == {"tool1", "tool3"}


@pytest.mark.ai
def test_compute_available_tools__preserves_tool_order__from_input() -> None:
    """
    Purpose: Verify function maintains the original order of tools.
    Why this matters: Tool order may be significant for priority or display.
    Setup summary: Provide ordered tools, assert result maintains same order.
    """
    # Arrange
    tools = [
        MockTool(name="zebra", is_enabled=True),
        MockTool(name="apple", is_enabled=True),
        MockTool(name="monkey", is_enabled=True),
    ]
    tool_choices: list[str] = []
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 3
    assert result[0].name == "zebra"
    assert result[1].name == "apple"
    assert result[2].name == "monkey"


@pytest.mark.ai
def test_compute_available_tools__returns_empty__when_all_tools_filtered_out() -> None:
    """
    Purpose: Verify function returns empty list when all tools are filtered.
    Why this matters: Edge case where no tools meet criteria should be handled.
    Setup summary: Disable all tools via disabled_tools list, assert empty result.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    tool_choices: list[str] = []
    disabled_tools: list[str] = ["tool1", "tool2"]

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert result == []


@pytest.mark.ai
def test_compute_available_tools__handles_duplicate_names_in_disabled_tools() -> None:
    """
    Purpose: Verify function handles duplicate tool names in disabled_tools list.
    Why this matters: Robust handling of malformed input prevents errors.
    Setup summary: Provide duplicates in disabled_tools, assert correct filtering.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
        MockTool(name="tool3", is_enabled=True),
    ]
    tool_choices: list[str] = []
    disabled_tools: list[str] = ["tool2", "tool2", "tool2"]

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 2
    assert {t.name for t in result} == {"tool1", "tool3"}


@pytest.mark.ai
def test_compute_available_tools__handles_nonexistent_names_in_tool_choices() -> None:
    """
    Purpose: Verify function handles tool_choices with names not in tools list.
    Why this matters: Invalid configuration should not cause errors.
    Setup summary: Provide tool_choices with nonexistent names, assert valid tools returned.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    tool_choices: list[str] = ["tool1", "nonexistent", "another_fake"]
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 1
    assert result[0].name == "tool1"


@pytest.mark.ai
def test_compute_available_tools__handles_nonexistent_names_in_disabled_tools() -> None:
    """
    Purpose: Verify function handles disabled_tools with names not in tools list.
    Why this matters: Invalid configuration should not cause errors.
    Setup summary: Provide disabled_tools with nonexistent names, assert no impact.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    tool_choices: list[str] = []
    disabled_tools: list[str] = ["nonexistent", "fake_tool"]

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 2
    assert {t.name for t in result} == {"tool1", "tool2"}


@pytest.mark.ai
def test_compute_available_tools__exclusive_tool_respects_is_enabled_check() -> None:
    """
    Purpose: Verify exclusive tool is still filtered if is_enabled() returns False.
    Why this matters: is_enabled check should apply to all tools including exclusive ones.
    Setup summary: Create disabled exclusive tool in tool_choices, assert it's excluded.
    """
    # Arrange
    tools = [
        MockTool(name="exclusive", is_enabled=False, is_exclusive=True),
        MockTool(name="regular", is_enabled=True, is_exclusive=False),
    ]
    tool_choices: list[str] = ["exclusive", "regular"]
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 1
    assert result[0].name == "regular"


@pytest.mark.ai
def test_compute_available_tools__exclusive_tool_respects_disabled_tools_list() -> None:
    """
    Purpose: Verify exclusive tool is filtered if in disabled_tools list.
    Why this matters: disabled_tools should apply to all tools including exclusive ones.
    Setup summary: Add exclusive tool to disabled_tools, assert it's excluded.
    """
    # Arrange
    tools = [
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
        MockTool(name="regular", is_enabled=True, is_exclusive=False),
    ]
    tool_choices: list[str] = ["exclusive", "regular"]
    disabled_tools: list[str] = ["exclusive"]

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == 1
    assert result[0].name == "regular"


@pytest.mark.ai
@pytest.mark.parametrize(
    "tool_names,expected_count",
    [
        (["tool1"], 1),
        (["tool1", "tool2"], 2),
        (["tool1", "tool2", "tool3"], 3),
        (["tool1", "tool2", "tool3", "tool4", "tool5"], 5),
    ],
    ids=["one-tool", "two-tools", "three-tools", "five-tools"],
)
def test_compute_available_tools__handles_various_tool_counts(
    tool_names: list[str], expected_count: int
) -> None:
    """
    Purpose: Verify function scales correctly with different numbers of tools.
    Why this matters: Ensures performance and correctness across various scales.
    Setup summary: Parametrized test with different tool counts.
    """
    # Arrange
    tools = [MockTool(name=name, is_enabled=True) for name in tool_names]
    tool_choices: list[str] = []
    disabled_tools: list[str] = []

    # Act
    result = _compute_available_tools(tools, tool_choices, disabled_tools)

    # Assert
    assert len(result) == expected_count


# ==================== Tests for _get_forced_tool_definition ====================


@pytest.mark.ai
def test_get_forced_tool_definition__returns_responses_api_format__when_responses_api_true() -> None:
    """
    Purpose: Verify function returns correct format for responses API.
    Why this matters: Ensures compatibility with OpenAI responses API.
    Setup summary: Call with responses_api=True, assert correct structure.
    """
    # Arrange
    tool_name = "search_tool"
    responses_api = True

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result == {
        "name": "search_tool",
        "type": "function",
    }
    assert "name" in result
    assert "type" in result
    assert "function" not in result


@pytest.mark.ai
def test_get_forced_tool_definition__returns_chat_completion_format__when_responses_api_false() -> None:
    """
    Purpose: Verify function returns correct format for chat completion API.
    Why this matters: Ensures compatibility with OpenAI chat completion API.
    Setup summary: Call with responses_api=False, assert correct structure.
    """
    # Arrange
    tool_name = "weather_tool"
    responses_api = False

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result == {
        "type": "function",
        "function": {"name": "weather_tool"},
    }
    assert "type" in result
    assert "function" in result
    assert "name" in result["function"]


@pytest.mark.ai
def test_get_forced_tool_definition__includes_tool_name__in_responses_api_format() -> None:
    """
    Purpose: Verify tool name is correctly included in responses API format.
    Why this matters: Tool name is essential for identifying which tool to force.
    Setup summary: Provide tool name with responses_api=True, assert name is set.
    """
    # Arrange
    tool_name = "calculator"
    responses_api = True

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["name"] == "calculator"
    assert result["type"] == "function"


@pytest.mark.ai
def test_get_forced_tool_definition__includes_tool_name__in_chat_completion_format() -> None:
    """
    Purpose: Verify tool name is correctly nested in chat completion format.
    Why this matters: Tool name must be in function object for chat completion API.
    Setup summary: Provide tool name with responses_api=False, assert name in function.
    """
    # Arrange
    tool_name = "translator"
    responses_api = False

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["function"]["name"] == "translator"
    assert result["type"] == "function"


@pytest.mark.ai
@pytest.mark.parametrize(
    "tool_name",
    [
        "simple_tool",
        "tool_with_underscores",
        "tool123",
        "UPPERCASE_TOOL",
        "MixedCaseTool",
    ],
    ids=["simple", "underscores", "with-numbers", "uppercase", "mixed-case"],
)
def test_get_forced_tool_definition__handles_various_tool_names__in_responses_api(
    tool_name: str,
) -> None:
    """
    Purpose: Verify function handles different tool name formats in responses API.
    Why this matters: Tool names can have various valid formats.
    Setup summary: Parametrized test with different tool name patterns.
    """
    # Arrange
    responses_api = True

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["name"] == tool_name
    assert result["type"] == "function"


@pytest.mark.ai
@pytest.mark.parametrize(
    "tool_name",
    [
        "simple_tool",
        "tool_with_underscores",
        "tool123",
        "UPPERCASE_TOOL",
        "MixedCaseTool",
    ],
    ids=["simple", "underscores", "with-numbers", "uppercase", "mixed-case"],
)
def test_get_forced_tool_definition__handles_various_tool_names__in_chat_completion(
    tool_name: str,
) -> None:
    """
    Purpose: Verify function handles different tool name formats in chat completion API.
    Why this matters: Tool names can have various valid formats.
    Setup summary: Parametrized test with different tool name patterns.
    """
    # Arrange
    responses_api = False

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["function"]["name"] == tool_name
    assert result["type"] == "function"


@pytest.mark.ai
def test_get_forced_tool_definition__type_field_always_function__for_responses_api() -> None:
    """
    Purpose: Verify type field is always set to 'function' in responses API format.
    Why this matters: OpenAI API requires type field to be 'function'.
    Setup summary: Call with responses_api=True, assert type is 'function'.
    """
    # Arrange
    tool_name = "any_tool"
    responses_api = True

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["type"] == "function"


@pytest.mark.ai
def test_get_forced_tool_definition__type_field_always_function__for_chat_completion() -> None:
    """
    Purpose: Verify type field is always set to 'function' in chat completion format.
    Why this matters: OpenAI API requires type field to be 'function'.
    Setup summary: Call with responses_api=False, assert type is 'function'.
    """
    # Arrange
    tool_name = "any_tool"
    responses_api = False

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["type"] == "function"


@pytest.mark.ai
def test_get_forced_tool_definition__responses_api_format_has_two_keys() -> None:
    """
    Purpose: Verify responses API format contains exactly two keys.
    Why this matters: Extra keys could cause API errors or unexpected behavior.
    Setup summary: Call with responses_api=True, assert exactly two keys.
    """
    # Arrange
    tool_name = "test_tool"
    responses_api = True

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert len(result) == 2
    assert set(result.keys()) == {"name", "type"}


@pytest.mark.ai
def test_get_forced_tool_definition__chat_completion_format_has_two_keys() -> None:
    """
    Purpose: Verify chat completion format contains exactly two top-level keys.
    Why this matters: Extra keys could cause API errors or unexpected behavior.
    Setup summary: Call with responses_api=False, assert exactly two top-level keys.
    """
    # Arrange
    tool_name = "test_tool"
    responses_api = False

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert len(result) == 2
    assert set(result.keys()) == {"type", "function"}
    assert len(result["function"]) == 1
    assert set(result["function"].keys()) == {"name"}


@pytest.mark.ai
def test_get_forced_tool_definition__empty_string_tool_name__responses_api() -> None:
    """
    Purpose: Verify function handles empty string tool name in responses API.
    Why this matters: Edge case handling prevents unexpected behavior.
    Setup summary: Provide empty string, assert it's included in result.
    """
    # Arrange
    tool_name = ""
    responses_api = True

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["name"] == ""
    assert result["type"] == "function"


@pytest.mark.ai
def test_get_forced_tool_definition__empty_string_tool_name__chat_completion() -> None:
    """
    Purpose: Verify function handles empty string tool name in chat completion format.
    Why this matters: Edge case handling prevents unexpected behavior.
    Setup summary: Provide empty string, assert it's included in nested structure.
    """
    # Arrange
    tool_name = ""
    responses_api = False

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["function"]["name"] == ""
    assert result["type"] == "function"


@pytest.mark.ai
def test_get_forced_tool_definition__special_characters_in_tool_name__responses_api() -> None:
    """
    Purpose: Verify function handles tool names with special characters in responses API.
    Why this matters: Tool names might contain hyphens, dots, or other characters.
    Setup summary: Provide tool name with special characters, assert it's preserved.
    """
    # Arrange
    tool_name = "tool-with.special_chars@123"
    responses_api = True

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["name"] == "tool-with.special_chars@123"
    assert result["type"] == "function"


@pytest.mark.ai
def test_get_forced_tool_definition__special_characters_in_tool_name__chat_completion() -> None:
    """
    Purpose: Verify function handles tool names with special characters in chat completion.
    Why this matters: Tool names might contain hyphens, dots, or other characters.
    Setup summary: Provide tool name with special characters, assert it's preserved.
    """
    # Arrange
    tool_name = "tool-with.special_chars@123"
    responses_api = False

    # Act
    result: dict[str, Any] = _get_forced_tool_definition(tool_name, responses_api)  # type: ignore[assignment]

    # Assert
    assert result["function"]["name"] == "tool-with.special_chars@123"
    assert result["type"] == "function"


@pytest.mark.ai
def test_get_forced_tool_definition__consistent_behavior__for_same_inputs() -> None:
    """
    Purpose: Verify function returns consistent results for same inputs.
    Why this matters: Deterministic behavior is essential for reliability.
    Setup summary: Call function multiple times with same inputs, assert identical results.
    """
    # Arrange
    tool_name = "consistent_tool"

    # Act
    result1: dict[str, Any] = _get_forced_tool_definition(tool_name, True)  # type: ignore[assignment]
    result2: dict[str, Any] = _get_forced_tool_definition(tool_name, True)  # type: ignore[assignment]
    result3: dict[str, Any] = _get_forced_tool_definition(tool_name, False)  # type: ignore[assignment]
    result4: dict[str, Any] = _get_forced_tool_definition(tool_name, False)  # type: ignore[assignment]

    # Assert
    assert result1 == result2
    assert result3 == result4
    assert result1 != result3  # Different API formats should differ



# ==================== Fixtures for ToolManager Tests ====================


@pytest.fixture
def default_config() -> ToolManagerConfig:
    """Create default ToolManagerConfig for testing."""
    return ToolManagerConfig()


@pytest.fixture
def custom_config() -> ToolManagerConfig:
    """Create custom ToolManagerConfig for testing."""
    return ToolManagerConfig(max_tool_calls=5, log_exceptions_to_debug_info=False)


@pytest.fixture
def mock_builtin_tool() -> MockBuiltInTool:
    """Create a mock built-in tool."""
    return MockBuiltInTool(name="code_interpreter", is_enabled=True)


@pytest.fixture
def mixed_tools() -> tuple[list[MockTool], list[MockTool], list[MockBuiltInTool]]:
    """Create mixed set of regular, a2a (subclass of Tool), and builtin tools."""
    regular_tools = [
        MockTool(name="search", is_enabled=True),
        MockTool(name="weather", is_enabled=True),
    ]
    a2a_tools = [
        MockTool(name="sub_agent_1", is_enabled=True),  # SubAgentTool is a Tool subclass
    ]
    builtin_tools = [
        MockBuiltInTool(name="code_interpreter", is_enabled=True),
    ]
    return regular_tools, a2a_tools, builtin_tools


# ==================== A. Tool Filtering & Availability Tests ====================


@pytest.mark.ai
def test_tool_manager__initialization__sets_available_tools_correctly(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify ToolManager initialization correctly sets available tools.
    Why this matters: Initialization is the foundation of all tool management.
    Setup summary: Create manager with mixed tools, assert correct availability.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    a2a_tools = [MockTool(name="a2a_tool", is_enabled=True)]
    mcp_tools = [MockTool(name="mcp_tool", is_enabled=True)]
    builtin_tools = [MockBuiltInTool(name="builtin", is_enabled=True)]

    # Act
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=a2a_tools,  # type: ignore[arg-type]
        mcp_tools=mcp_tools,  # type: ignore[arg-type]
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
    )

    # Assert
    all_tools = manager.get_available_tools()
    assert len(all_tools) == 4  # tools + a2a + mcp (all are Tool type)
    assert {t.name for t in all_tools} == {"tool1", "tool2", "a2a_tool", "mcp_tool"}


@pytest.mark.ai
def test_tool_manager__initialization__filters_disabled_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify disabled tools are filtered out during initialization.
    Why this matters: Disabled tools should not be available for use.
    Setup summary: Create tools with some disabled, assert they're excluded.
    """
    # Arrange
    tools = [
        MockTool(name="enabled", is_enabled=True),
        MockTool(name="disabled", is_enabled=False),
    ]

    # Act
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 1
    assert available[0].name == "enabled"


@pytest.mark.ai
def test_tool_manager__initialization__respects_disabled_tools_list(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify disabled_tools parameter filters tools correctly.
    Why this matters: Users can explicitly disable specific tools.
    Setup summary: Pass disabled_tools list, assert those tools are excluded.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
        MockTool(name="tool3", is_enabled=True),
    ]
    disabled_tools = ["tool2"]

    # Act
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        disabled_tools=disabled_tools,
    )

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 2
    assert {t.name for t in available} == {"tool1", "tool3"}


@pytest.mark.ai
def test_tool_manager__initialization__respects_tool_choices(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify tool_choices parameter filters to only selected tools.
    Why this matters: Users can explicitly select specific tools to use.
    Setup summary: Pass tool_choices list, assert only those tools available.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
        MockTool(name="tool3", is_enabled=True),
    ]
    tool_choices = ["tool1", "tool3"]

    # Act
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=tool_choices,
    )

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 2
    assert {t.name for t in available} == {"tool1", "tool3"}


@pytest.mark.ai
def test_tool_manager__initialization__exclusive_tool_overrides_all_others(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify exclusive tool in tool_choices makes only that tool available.
    Why this matters: Exclusive tools should take complete control.
    Setup summary: Include exclusive tool in choices, assert it's the only one.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
        MockTool(name="tool3", is_enabled=True),
    ]
    tool_choices = ["tool1", "exclusive", "tool3"]

    # Act
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=tool_choices,
    )

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 1
    assert available[0].name == "exclusive"
    assert available[0].is_exclusive()


@pytest.mark.ai
def test_tool_manager__initialization__exclusive_tool_excluded_without_choices(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify exclusive tools are excluded when tool_choices is empty.
    Why this matters: Exclusive tools require explicit selection.
    Setup summary: Include exclusive tool without choices, assert it's excluded.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
        MockTool(name="tool3", is_enabled=True),
    ]

    # Act
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=[],
    )

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 2
    assert {t.name for t in available} == {"tool1", "tool3"}


@pytest.mark.ai
def test_tool_manager__initialization__disabled_tools_override_tool_choices(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify disabled_tools takes precedence over tool_choices.
    Why this matters: Explicit disabling should override explicit enabling.
    Setup summary: Add same tool to both lists, assert it's excluded.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    tool_choices = ["tool1", "tool2"]
    disabled_tools = ["tool2"]

    # Act
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=tool_choices,
        disabled_tools=disabled_tools,
    )

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 1
    assert available[0].name == "tool1"


@pytest.mark.ai
def test_tool_manager__initialization__all_tools_disabled__returns_empty(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify manager handles case where all tools are disabled.
    Why this matters: Edge case that should not crash the system.
    Setup summary: Disable all tools, assert empty available list.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=False),
        MockTool(name="tool2", is_enabled=False),
    ]

    # Act
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 0


@pytest.mark.ai
def test_tool_manager__initialization__empty_tool_lists__returns_empty(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify manager handles initialization with no tools.
    Why this matters: Edge case that should not crash the system.
    Setup summary: Pass empty tool lists, assert empty available list.
    """
    # Act
    manager = ToolManager(
        config=default_config,
        tools=[],
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Assert
    assert len(manager.get_available_tools()) == 0
    assert manager.get_exclusive_tools() == []


# ==================== B. Tool Retrieval & Lookup Tests ====================


@pytest.mark.ai
def test_tool_manager__get_tool_by_name__returns_correct_tool(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_by_name returns the correct tool.
    Why this matters: Core lookup functionality for tool execution.
    Setup summary: Create manager with tools, lookup by name, assert correct tool.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True),
        MockTool(name="weather", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Act
    result = manager.get_tool_by_name("search")

    # Assert
    assert result is not None
    assert result.name == "search"


@pytest.mark.ai
def test_tool_manager__get_tool_by_name__returns_none_for_missing_tool(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_by_name returns None for non-existent tool.
    Why this matters: Graceful handling of invalid tool names.
    Setup summary: Lookup non-existent tool name, assert None returned.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Act
    result = manager.get_tool_by_name("nonexistent")

    # Assert
    assert result is None


@pytest.mark.ai
def test_tool_manager__get_tool_by_name__returns_none_for_builtin_tool(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_by_name returns None for built-in tools.
    Why this matters: Built-in tools should use separate getter.
    Setup summary: Lookup built-in tool with get_tool_by_name, assert None.
    """
    # Arrange
    builtin = MockBuiltInTool(name="code_interpreter", is_enabled=True)
    manager = ToolManager(
        config=default_config,
        tools=[],
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[builtin],  # type: ignore[arg-type]
    )

    # Act
    result = manager.get_tool_by_name("code_interpreter")

    # Assert
    assert result is None


@pytest.mark.ai
def test_tool_manager__get_tool_by_name__returns_tool_even_if_disabled(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_by_name returns tool even if disabled.
    Why this matters: get_tool_by_name searches all tools for lookup purposes (e.g., add_forced_tool).
    Setup summary: Lookup tool that was disabled, assert it's still returned.
    """
    # Arrange
    tools = [MockTool(name="disabled_tool", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        disabled_tools=["disabled_tool"],
    )

    # Act
    result = manager.get_tool_by_name("disabled_tool")

    # Assert
    assert result is not None
    assert result.name == "disabled_tool"


@pytest.mark.ai
def test_tool_manager__get_builtin_tool_by_name__returns_correct_tool(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_builtin_tool_by_name returns the correct built-in tool.
    Why this matters: Built-in tools need separate lookup mechanism.
    Setup summary: Create manager with built-in tool, lookup, assert correct tool.
    """
    # Arrange
    builtin = MockBuiltInTool(name="code_interpreter", is_enabled=True)
    manager = ToolManager(
        config=default_config,
        tools=[],
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[builtin],  # type: ignore[arg-type]
    )

    # Act
    result = manager.get_builtin_tool_by_name("code_interpreter")

    # Assert
    assert result is not None
    assert result.name == "code_interpreter"


@pytest.mark.ai
def test_tool_manager__get_builtin_tool_by_name__returns_none_for_regular_tool(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_builtin_tool_by_name returns None for regular tools.
    Why this matters: Regular tools should use separate getter.
    Setup summary: Lookup regular tool with get_builtin_tool_by_name, assert None.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Act
    result = manager.get_builtin_tool_by_name("search")

    # Assert
    assert result is None


@pytest.mark.ai
def test_tool_manager__get_tools__returns_only_tool_instances(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tools returns only Tool instances, not built-in tools.
    Why this matters: Tool execution expects Tool interface.
    Setup summary: Create manager with mixed types, assert get_tools filters correctly.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    builtin_tools = [MockBuiltInTool(name="code_interpreter", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
    )

    # Act
    result = manager.get_available_tools()

    # Assert
    assert len(result) == 1
    assert result[0].name == "search"
    assert all(isinstance(t, MockTool) for t in result)


@pytest.mark.ai
def test_tool_manager__get_available_tools__excludes_builtin_by_default(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_available_tools excludes builtin tools by default.
    Why this matters: Default behavior should match tool execution expectations.
    Setup summary: Create manager with mixed tool types, verify only Tool instances returned.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True),
        MockTool(name="calculator", is_enabled=True),
    ]
    builtin_tools = [MockBuiltInTool(name="code_interpreter", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
    )

    # Act
    result = manager.get_available_tools()

    # Assert
    assert len(result) == 2
    assert {t.name for t in result} == {"search", "calculator"}
    assert all(isinstance(t, MockTool) for t in result)


@pytest.mark.ai
def test_tool_manager__get_available_tools__includes_builtin_when_requested(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_available_tools includes builtin tools when flag is True.
    Why this matters: LLM needs both tool types when include_builtin_tools=True.
    Setup summary: Create manager with mixed types, verify all tools returned with flag.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True),
        MockTool(name="calculator", is_enabled=True),
    ]
    builtin_tools = [
        MockBuiltInTool(name="code_interpreter", is_enabled=True),
        MockBuiltInTool(name="file_search", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
    )

    # Act
    result = manager.get_available_tools(include_builtin_tools=True)

    # Assert
    assert len(result) == 4
    tool_names = {t.name for t in result}
    assert tool_names == {"search", "calculator", "code_interpreter", "file_search"}


@pytest.mark.ai
def test_tool_manager__get_available_tools__respects_filtering_with_builtin_flag(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify include_builtin_tools respects tool_choices and disabled_tools.
    Why this matters: Filtering should apply regardless of include_builtin_tools setting.
    Setup summary: Create filtered manager, verify builtin flag doesn't bypass filters.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True),
        MockTool(name="calculator", is_enabled=True),
    ]
    builtin_tools = [
        MockBuiltInTool(name="code_interpreter", is_enabled=True),
        MockBuiltInTool(name="file_search", is_enabled=True),
    ]
    tool_choices = ["search", "code_interpreter"]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
        tool_choices=tool_choices,
    )

    # Act
    result_without_builtin = manager.get_available_tools()
    result_with_builtin = manager.get_available_tools(include_builtin_tools=True)

    # Assert
    assert len(result_without_builtin) == 1
    assert result_without_builtin[0].name == "search"
    
    assert len(result_with_builtin) == 2
    assert {t.name for t in result_with_builtin} == {"search", "code_interpreter"}


@pytest.mark.ai
def test_tool_manager__get_exclusive_tools__returns_only_exclusive_tool_names(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_exclusive_tools returns names of exclusive tools only.
    Why this matters: Exclusive tools need special handling in tool forcing.
    Setup summary: Create mix of exclusive/regular tools, assert only exclusive returned.
    """
    # Arrange
    tools = [
        MockTool(name="regular", is_enabled=True, is_exclusive=False),
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
    ]
    tool_choices = ["regular", "exclusive"]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=tool_choices,
    )

    # Act
    result = manager.get_exclusive_tools()

    # Assert
    assert result == ["exclusive"]


@pytest.mark.ai
def test_tool_manager__get_exclusive_tools__returns_empty_when_none_exclusive(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_exclusive_tools returns empty list when no exclusive tools.
    Why this matters: Common case needs to handle gracefully.
    Setup summary: Create only regular tools, assert empty exclusive list.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True, is_exclusive=False),
        MockTool(name="tool2", is_enabled=True, is_exclusive=False),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Act
    result = manager.get_exclusive_tools()

    # Assert
    assert result == []


@pytest.mark.ai
def test_tool_manager__get_exclusive_tools__returns_all_regardless_of_availability(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_exclusive_tools returns exclusive tools even when disabled.
    Why this matters: The method reports tool configuration, not availability status.
    Setup summary: Create disabled exclusive tool, verify it's still in the list.
    """
    # Arrange
    tools = [
        MockTool(name="regular", is_enabled=True, is_exclusive=False),
        MockTool(name="exclusive_enabled", is_enabled=True, is_exclusive=True),
        MockTool(name="exclusive_disabled", is_enabled=False, is_exclusive=True),
    ]
    disabled_tools = ["exclusive_enabled"]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        disabled_tools=disabled_tools,
    )

    # Act
    result = manager.get_exclusive_tools()

    # Assert - Both exclusive tools returned regardless of availability
    assert set(result) == {"exclusive_enabled", "exclusive_disabled"}


@pytest.mark.ai
def test_tool_manager__get_tool_choices__returns_copy_of_choices(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_choices returns a copy, not the original list.
    Why this matters: Prevents external mutation of internal state.
    Setup summary: Get choices, mutate result, verify original unchanged.
    """
    # Arrange
    tool_choices = ["tool1", "tool2"]
    manager = ToolManager(
        config=default_config,
        tools=[MockTool(name="tool1", is_enabled=True)],  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=tool_choices,
    )

    # Act
    result = manager.get_tool_choices()
    result.append("tool3")

    # Assert
    assert manager.get_tool_choices() == ["tool1", "tool2"]
    assert "tool3" not in manager.get_tool_choices()


# ==================== C. Tool Definition Generation Tests ====================


@pytest.mark.ai
def test_tool_manager__get_tool_definitions__excludes_builtin_by_default(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_definitions excludes built-in tools by default.
    Why this matters: Default behavior should return only regular tool definitions.
    Setup summary: Create only regular tools, call without args, assert correct definitions.
    """
    # Arrange
    tools = [
        MockTool(name="search", is_enabled=True),
        MockTool(name="weather", is_enabled=True),
    ]
    # Note: Not including builtin tools in this test since MockBuiltInTool doesn't inherit from OpenAIBuiltInTool
    # The builtin exclusion logic is tested in test_tool_manager__get_tool_definitions__includes_builtin_when_requested
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Act
    result = manager.get_tool_definitions()

    # Assert
    assert len(result) == 2
    assert all(isinstance(r, LanguageModelToolDescription) for r in result)
    assert {r.name for r in result} == {"search", "weather"}


@pytest.mark.ai
def test_tool_manager__get_tool_definitions__includes_builtin_when_requested(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_definitions includes built-in tools when flag is True.
    Why this matters: Some contexts need both tool types.
    Setup summary: Create mixed tools, call with flag, assert both types included.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    builtin_tools = [MockBuiltInTool(name="code_interpreter", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
    )

    # Act
    result = manager.get_tool_definitions(include_builtin_tools=True)

    # Assert
    assert len(result) == 2
    # First is regular tool, second is built-in
    assert isinstance(result[0], LanguageModelToolDescription)
    assert result[0].name == "search"
    assert isinstance(result[1], dict)
    assert result[1]["type"] == "code_interpreter"


@pytest.mark.ai
def test_tool_manager__get_tool_definitions__returns_empty_when_no_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_definitions returns empty list when no tools available.
    Why this matters: Edge case should not crash.
    Setup summary: Create manager with no tools, assert empty list.
    """
    # Arrange
    manager = ToolManager(
        config=default_config,
        tools=[],
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Act
    result = manager.get_tool_definitions()

    # Assert
    assert result == []


@pytest.mark.ai
def test_tool_manager__get_tool_definitions__respects_current_availability(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_definitions only includes currently available tools.
    Why this matters: Disabled tools should not appear in definitions.
    Setup summary: Create tools with some disabled, assert only enabled in definitions.
    """
    # Arrange
    tools = [
        MockTool(name="enabled", is_enabled=True),
        MockTool(name="disabled", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        disabled_tools=["disabled"],
    )

    # Act
    result = manager.get_tool_definitions()

    # Assert
    assert len(result) == 1
    assert result[0].name == "enabled"


@pytest.mark.ai
def test_tool_manager__get_forced_tools__returns_definitions_for_tool_choices(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_forced_tools returns definitions for tools in tool_choices.
    Why this matters: Forced tools need correct format for API.
    Setup summary: Create manager with tool_choices, assert forced definitions returned.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    tool_choices = ["tool1"    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=tool_choices,
    )

    # Act
    result = manager.get_forced_tools(responses_api=False)

    # Assert
    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "tool1"


@pytest.mark.ai
def test_tool_manager__get_forced_tools__returns_empty_when_no_choices(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_forced_tools returns empty list when no tool_choices.
    Why this matters: No forced tools should be indicated by empty list.
    Setup summary: Create manager without tool_choices, assert empty forced list.
    """
    # Arrange
    tools = [MockTool(name="tool1", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=[],
    )

    # Act
    result = manager.get_forced_tools()

    # Assert
    assert result == []


@pytest.mark.ai
def test_tool_manager__get_forced_tools__uses_responses_api_format_when_requested(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_forced_tools returns responses API format when flag is True.
    Why this matters: Different APIs require different formats.
    Setup summary: Call with responses_api=True, assert correct format.
    """
    # Arrange
    tools = [MockTool(name="tool1", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=["tool1"],
    )

    # Act
    result = manager.get_forced_tools(responses_api=True)

    # Assert
    assert len(result) == 1
    assert result[0]["type"] == "function"  # type: ignore[index]
    assert result[0]["name"] == "tool1"  # type: ignore[index, typeddict-item]
    assert "function" not in result[0]  # Different structure than chat completion


@pytest.mark.ai
def test_tool_manager__get_forced_tools__excludes_builtin_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_forced_tools excludes built-in tools even if in choices.
    Why this matters: Built-in tools cannot be forced per API limitation.
    Setup summary: Add built-in to choices, assert it's not in forced list.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    builtin_tools = [MockBuiltInTool(name="code_interpreter", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
        tool_choices=["search", "code_interpreter"],
    )

    # Act
    result = manager.get_forced_tools()

    # Assert
    assert len(result) == 1
    assert result[0]["function"]["name"] == "search"


@pytest.mark.ai
def test_tool_manager__get_tool_prompts__returns_prompts_for_all_available_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_prompts returns prompts for all available tools.
    Why this matters: Prompts are needed for tool usage instructions.
    Setup summary: Create manager with tools, assert prompts for all available.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Act
    result = manager.get_tool_prompts()

    # Assert
    assert len(result) == 2
    assert all(isinstance(p, ToolPrompts) for p in result)
    assert {p.name for p in result} == {"tool1", "tool2"}


@pytest.mark.ai
def test_tool_manager__get_tool_prompts__includes_builtin_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify get_tool_prompts includes prompts for built-in tools.
    Why this matters: Built-in tools also need usage instructions.
    Setup summary: Create mixed tools, assert prompts include built-ins.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    builtin_tools = [MockBuiltInTool(name="code_interpreter", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
    )

    # Act
    result = manager.get_tool_prompts()

    # Assert
    assert len(result) == 2
    assert {p.name for p in result} == {"search", "code_interpreter"}


# ==================== D. State Mutation Operations Tests ====================


@pytest.mark.ai
def test_tool_manager__add_forced_tool__adds_tool_to_choices(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify add_forced_tool adds tool name to tool_choices.
    Why this matters: Core state mutation for forcing tools.
    Setup summary: Start with empty choices, add tool, assert it's in choices.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=[],
    )

    # Act
    manager.add_forced_tool("search")

    # Assert
    assert "search" in manager.get_tool_choices()
    assert manager.get_tool_choices() == ["search"]


@pytest.mark.ai
def test_tool_manager__add_forced_tool__updates_available_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify add_forced_tool triggers availability update.
    Why this matters: Tool availability must reflect current choices.
    Setup summary: Start with multiple tools, add one as forced, verify availability.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
        MockTool(name="tool3", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=[],
    )

    # Act
    manager.add_forced_tool("tool2")

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 1
    assert available[0].name == "tool2"


@pytest.mark.ai
def test_tool_manager__add_forced_tool__is_idempotent(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify adding same tool twice doesn't duplicate in choices.
    Why this matters: Idempotency prevents list pollution.
    Setup summary: Add same tool twice, assert it appears once in choices.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=[],
    )

    # Act
    manager.add_forced_tool("search")
    manager.add_forced_tool("search")

    # Assert
    choices = manager.get_tool_choices()
    assert choices.count("search") == 1
    assert len(choices) == 1


@pytest.mark.ai
def test_tool_manager__add_forced_tool__raises_error_for_nonexistent_tool(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify add_forced_tool raises ValueError for non-existent tool.
    Why this matters: Invalid tool names should be caught early.
    Setup summary: Try to add non-existent tool, assert ValueError raised.
    """
    # Arrange
    tools = [MockTool(name="search", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Tool nonexistent not found"):
        manager.add_forced_tool("nonexistent")


@pytest.mark.ai
def test_tool_manager__add_forced_tool__raises_error_for_builtin_tool(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify add_forced_tool raises error when trying to force built-in tool.
    Why this matters: Built-in tools cannot be forced per design.
    Setup summary: Try to force built-in tool, assert error raised.
    """
    # Arrange
    builtin_tools = [MockBuiltInTool(name="code_interpreter", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=[],
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=builtin_tools,  # type: ignore[arg-type]
    )

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        manager.add_forced_tool("code_interpreter")


@pytest.mark.ai
def test_tool_manager__add_forced_tool__allows_adding_multiple_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify multiple tools can be added to forced list sequentially.
    Why this matters: Users may want to force multiple tools.
    Setup summary: Add multiple tools, assert all in choices.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
        MockTool(name="tool3", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=[],
    )

    # Act
    manager.add_forced_tool("tool1")
    manager.add_forced_tool("tool3")

    # Assert
    choices = manager.get_tool_choices()
    assert len(choices) == 2
    assert set(choices) == {"tool1", "tool3"}


@pytest.mark.ai
def test_tool_manager__clear_forced_tools__removes_all_tool_choices(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify clear_forced_tools removes all tools from choices.
    Why this matters: Users need ability to reset forced tools.
    Setup summary: Start with forced tools, clear, assert empty choices.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=["tool1", "tool2"],
    )

    # Act
    manager.clear_forced_tools()

    # Assert
    assert manager.get_tool_choices() == []


@pytest.mark.ai
def test_tool_manager__clear_forced_tools__updates_available_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify clear_forced_tools triggers availability update.
    Why this matters: Availability should reflect no forced tools.
    Setup summary: Start with one forced tool, clear, assert all tools available.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
        MockTool(name="tool3", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=["tool1"],
    )

    # Act
    manager.clear_forced_tools()

    # Assert
    available = manager.get_available_tools()
    assert len(available) == 3
    assert {t.name for t in available} == {"tool1", "tool2", "tool3"}


@pytest.mark.ai
def test_tool_manager__clear_forced_tools__is_idempotent(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify calling clear_forced_tools multiple times is safe.
    Why this matters: Idempotency prevents errors.
    Setup summary: Clear twice, assert no errors and choices remain empty.
    """
    # Arrange
    tools = [MockTool(name="tool1", is_enabled=True)]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=["tool1"],
    )

    # Act
    manager.clear_forced_tools()
    manager.clear_forced_tools()

    # Assert
    assert manager.get_tool_choices() == []


@pytest.mark.ai
def test_tool_manager__state_transition__add_then_clear_then_add_again(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify state transitions work correctly through add/clear cycle.
    Why this matters: Complex state transitions must be robust.
    Setup summary: Add tool, clear, add different tool, verify correct state.
    """
    # Arrange
    tools = [
        MockTool(name="tool1", is_enabled=True),
        MockTool(name="tool2", is_enabled=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=[],
    )

    # Act & Assert - Initial state
    assert manager.get_tool_choices() == []
    assert len(manager.get_available_tools()) == 2

    # Add tool1
    manager.add_forced_tool("tool1")
    assert manager.get_tool_choices() == ["tool1"]
    assert len(manager.get_available_tools()) == 1
    assert manager.get_available_tools()[0].name == "tool1"

    # Clear
    manager.clear_forced_tools()
    assert manager.get_tool_choices() == []
    assert len(manager.get_available_tools()) == 2

    # Add tool2
    manager.add_forced_tool("tool2")
    assert manager.get_tool_choices() == ["tool2"]
    assert len(manager.get_available_tools()) == 1
    assert manager.get_available_tools()[0].name == "tool2"


@pytest.mark.ai
def test_tool_manager__state_transition__exclusive_tool_behavior_with_forced_tools(
    default_config: ToolManagerConfig,
) -> None:
    """
    Purpose: Verify exclusive tool overrides when added to forced tools.
    Why this matters: Exclusive tools should maintain override behavior.
    Setup summary: Force regular tool, then force exclusive, verify only exclusive available.
    """
    # Arrange
    tools = [
        MockTool(name="regular", is_enabled=True, is_exclusive=False),
        MockTool(name="exclusive", is_enabled=True, is_exclusive=True),
    ]
    manager = ToolManager(
        config=default_config,
        tools=tools,  # type: ignore[arg-type]
        a2a_tools=[],
        mcp_tools=[],
        builtin_tools=[],
        tool_choices=[],
    )

    # Act - Add regular tool first
    manager.add_forced_tool("regular")
    assert len(manager.get_available_tools()) == 1
    assert manager.get_available_tools()[0].name == "regular"

    # Add exclusive tool
    manager.add_forced_tool("exclusive")

    # Assert - Only exclusive tool should be available
    available = manager.get_available_tools()
    assert len(available) == 1
    assert available[0].name == "exclusive"
    assert available[0].is_exclusive()

