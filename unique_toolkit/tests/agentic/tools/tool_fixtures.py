"""
Fixtures for tool factory tests.

This module provides reusable fixtures for testing ToolFactory and Tool classes.
All fixtures return actual objects with proper type annotations for better type safety.
"""

from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig, ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class MockToolConfig(BaseToolConfig):
    """Test configuration for mock tool."""

    test_param: str = "default_value"
    optional_param: int = 42


class MockTool(Tool[MockToolConfig]):
    """Mock tool for testing purposes."""

    name = "test_tool"

    def __init__(self, configuration: MockToolConfig, *args, **kwargs):
        # Create a mock event for the parent constructor with required attributes
        mock_event = Mock(spec=ChatEvent)
        mock_event.company_id = "test_company"
        mock_event.user_id = "test_user"
        mock_event.chat_id = "test_chat"
        mock_event.assistant_id = "test_assistant"

        # Mock the payload structure
        mock_payload = Mock()
        mock_payload.assistant_message = Mock()
        mock_payload.assistant_message.id = "test_assistant_message_id"
        mock_event.payload = mock_payload

        super().__init__(configuration, mock_event)
        self.settings.configuration = configuration
        # settings will be set by factory, but we need to initialize it properly
        self.settings = ToolBuildConfig(name=self.name, configuration=configuration)

    def tool_description(self) -> LanguageModelToolDescription:
        """Return a mock tool description."""

        class TestParameters(BaseModel):
            test_param: str

        return LanguageModelToolDescription(
            name=self.name,
            description="A test tool for unit testing",
            parameters=TestParameters,
        )

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        """Mock implementation of the run method."""
        return ToolCallResponse(
            id=tool_call.id or "test_id",
            name=tool_call.name,
            content="Test tool response",
            debug_info={"test": "debug_info"},
            error_message="",
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        """Mock implementation for deprecated method."""
        return [EvaluationMetricName.CONTEXT_RELEVANCY]

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        """Mock implementation for deprecated method."""
        return [EvaluationMetricName.CONTEXT_RELEVANCY]


@pytest.fixture
def test_tool_config() -> MockToolConfig:
    """
    Base fixture for test tool configuration.

    Returns:
        MockToolConfig with default values for test cases.
    """
    return MockToolConfig(test_param="default_value", optional_param=42)


@pytest.fixture
def test_tool_class() -> type[Tool]:
    """
    Fixture providing the MockTool class.

    Returns:
        MockTool class for registration and instantiation.
    """
    return MockTool


@pytest.fixture
def test_tool_config_class() -> type[BaseToolConfig]:
    """
    Fixture providing the MockToolConfig class.

    Returns:
        MockToolConfig class for factory registration.
    """
    return MockToolConfig


@pytest.fixture
def mock_tool_build_config(test_tool_config: MockToolConfig) -> ToolBuildConfig:
    """
    Base fixture for ToolBuildConfig with default settings.

    Args:
        test_tool_config: The tool configuration to use.

    Returns:
        ToolBuildConfig with default values.
    """
    return ToolBuildConfig(
        name="test_tool",
        configuration=test_tool_config,
        display_name="Test Tool",
        icon=ToolIcon.BOOK,
        selection_policy=ToolSelectionPolicy.BY_USER,
        is_exclusive=False,
        is_sub_agent=False,
        is_enabled=True,
    )


@pytest.fixture
def mock_language_model_function() -> LanguageModelFunction:
    """
    Fixture providing a mock LanguageModelFunction for tool testing.

    Returns:
        LanguageModelFunction with test data.
    """
    return LanguageModelFunction(
        id="test_function_id",
        name="test_tool",
        arguments='{"test_param": "test_value"}',
    )
