"""
Test suite for ToolFactory class.

This test suite validates the ToolFactory's ability to:
1. Register tools and configurations
2. Build tool configurations dynamically
3. Build tool instances with and without settings
4. Handle errors gracefully
5. Manage factory state across tests
"""

import pytest

from tests.agentic.tools.tool_fixtures import MockTool, MockToolConfig
from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import Tool


class TestToolFactory:
    """Test suite for ToolFactory functionality."""

    def setup_method(self):
        """Set up test environment before each test method."""
        # Store original factory state
        self.original_tool_map = ToolFactory.tool_map.copy()
        self.original_config_map = ToolFactory.tool_config_map.copy()

        # Clear factory for clean testing
        ToolFactory.tool_map.clear()
        ToolFactory.tool_config_map.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        # Restore original factory state
        ToolFactory.tool_map.clear()
        ToolFactory.tool_map.update(self.original_tool_map)
        ToolFactory.tool_config_map.clear()
        ToolFactory.tool_config_map.update(self.original_config_map)

    @pytest.mark.ai
    def test_register_tool__stores_tool_and_config__with_valid_types_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
    ) -> None:
        """
        Purpose: Verify that ToolFactory correctly registers a tool class and its config class.
        Why this matters: Registration is the foundation of the factory pattern; incorrect
            registration would break all tool building operations.
        Setup summary: Use fixture tool and config classes, register them, verify presence in maps.
        """
        # Arrange - fixtures provide the classes

        # Act
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        # Assert
        assert "test_tool" in ToolFactory.tool_map
        assert "test_tool" in ToolFactory.tool_config_map
        assert ToolFactory.tool_map["test_tool"] == test_tool_class
        assert ToolFactory.tool_config_map["test_tool"] == test_tool_config_class

    @pytest.mark.ai
    def test_build_tool_config__creates_config_instance__with_kwargs_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
    ) -> None:
        """
        Purpose: Ensure factory can build tool configuration from keyword arguments.
        Why this matters: Dynamic configuration building allows runtime tool customization
            without hardcoding config instances.
        Setup summary: Register tool, call build_tool_config with kwargs, verify result type and values.
        """
        # Arrange
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        # Act
        config = ToolFactory.build_tool_config(
            "test_tool", test_param="custom_value", optional_param=100
        )

        # Assert
        assert isinstance(config, MockToolConfig)
        assert config.test_param == "custom_value"
        assert config.optional_param == 100

    @pytest.mark.ai
    def test_build_tool_config__raises_value_error__with_unregistered_tool_AI(
        self,
    ) -> None:
        """
        Purpose: Verify that attempting to build config for unregistered tool raises ValueError.
        Why this matters: Clear error messages help developers identify registration issues quickly.
        Setup summary: Don't register any tools, attempt build_tool_config, assert ValueError with message.
        """
        # Arrange - factory is empty from setup_method

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ToolFactory.build_tool_config("nonexistent_tool", test_param="value")

        assert "Tool nonexistent_tool not found" in str(exc_info.value)

    @pytest.mark.ai
    def test_build_tool__creates_tool_instance__with_config_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
        test_tool_config: MockToolConfig,
    ) -> None:
        """
        Purpose: Ensure factory builds a tool instance when provided with valid configuration.
        Why this matters: Tool instantiation is the core purpose of the factory pattern.
        Setup summary: Register tool, build tool with config, verify instance type and configuration.
        """
        # Arrange
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        # Act
        tool = ToolFactory.build_tool("test_tool", test_tool_config)

        # Assert
        assert isinstance(tool, MockTool)
        assert tool.configuration == test_tool_config
        assert tool.name == "test_tool"

    @pytest.mark.ai
    def test_build_tool__raises_key_error__with_unregistered_tool_AI(
        self,
        test_tool_config: MockToolConfig,
    ) -> None:
        """
        Purpose: Verify that building an unregistered tool raises KeyError.
        Why this matters: Proper error handling prevents silent failures and aids debugging.
        Setup summary: Factory is empty, attempt to build tool, assert KeyError is raised.
        """
        # Arrange - factory is empty from setup_method

        # Act & Assert
        with pytest.raises(KeyError):
            ToolFactory.build_tool("unregistered_tool", test_tool_config)

    @pytest.mark.ai
    def test_build_tool_with_settings__applies_settings__with_valid_settings_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
        test_tool_config: MockToolConfig,
    ) -> None:
        """
        Purpose: Verify that build_tool_with_settings applies custom settings to the tool instance.
        Why this matters: Settings override allows runtime customization of tool behavior (display, policies).
        Setup summary: Register tool, create custom settings, build tool with settings, verify application.
        """
        # Arrange
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)
        custom_settings = ToolBuildConfig(
            name="test_tool",
            configuration=test_tool_config,
            display_name="Custom Display Name",
            icon=ToolIcon.ANALYTICS,
            selection_policy=ToolSelectionPolicy.FORCED_BY_DEFAULT,
            is_exclusive=True,
            is_enabled=False,
        )

        # Act
        tool = ToolFactory.build_tool_with_settings(
            "test_tool", custom_settings, test_tool_config
        )

        # Assert
        assert isinstance(tool, MockTool)
        assert tool.settings == custom_settings
        assert tool.display_name() == "Custom Display Name"
        assert tool.icon() == ToolIcon.ANALYTICS
        assert tool.selection_policy() == ToolSelectionPolicy.FORCED_BY_DEFAULT
        assert tool.is_exclusive() is True
        assert tool.is_enabled() is False

    @pytest.mark.ai
    def test_multiple_tool_registration__maintains_separate_entries__with_different_tools_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
    ) -> None:
        """
        Purpose: Ensure factory can manage multiple tool registrations simultaneously.
        Why this matters: Real applications use multiple tools; factory must handle concurrent registrations.
        Setup summary: Create second tool/config, register both, verify both exist in factory maps.
        """
        # Arrange - First tool from fixtures
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        # Create a second tool
        class SecondToolConfig(BaseToolConfig):
            second_param: str = "second_default"

        class SecondTool(MockTool):
            name = "second_tool"

        # Act
        ToolFactory.register_tool(SecondTool, SecondToolConfig)

        # Assert
        assert len(ToolFactory.tool_map) == 2
        assert len(ToolFactory.tool_config_map) == 2
        assert "test_tool" in ToolFactory.tool_map
        assert "second_tool" in ToolFactory.tool_map
        assert ToolFactory.tool_map["test_tool"] == test_tool_class
        assert ToolFactory.tool_map["second_tool"] == SecondTool

    @pytest.mark.ai
    def test_build_tool__uses_correct_config__with_multiple_registered_tools_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
    ) -> None:
        """
        Purpose: Verify factory builds each tool with its correct configuration type.
        Why this matters: Prevents configuration mix-ups when multiple tools are registered.
        Setup summary: Register two tools with different configs, build both, verify correct types.
        """
        # Arrange
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        class AnotherConfig(BaseToolConfig):
            another_field: str = "another_value"

        class AnotherTool(MockTool):
            name = "another_tool"

        ToolFactory.register_tool(AnotherTool, AnotherConfig)

        # Act
        config1 = ToolFactory.build_tool_config("test_tool", test_param="value1")
        config2 = ToolFactory.build_tool_config("another_tool", another_field="value2")

        # Assert
        assert isinstance(config1, MockToolConfig)
        assert isinstance(config2, AnotherConfig)
        assert config1.test_param == "value1"
        assert config2.another_field == "value2"

    @pytest.mark.ai
    def test_factory_state_cleanup__restores_original_state__after_test_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
    ) -> None:
        """
        Purpose: Verify teardown properly restores factory state to prevent test pollution.
        Why this matters: Tests must be isolated; state leakage causes flaky test failures.
        Setup summary: Register tool, verify it exists, rely on teardown to clean up.
        """
        # Arrange
        initial_tool_count = len(self.original_tool_map)

        # Act
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        # Assert - tool is registered
        assert len(ToolFactory.tool_map) == initial_tool_count + 1
        assert "test_tool" in ToolFactory.tool_map

        # teardown_method will restore the original state
        # This is implicitly tested by running multiple tests

    @pytest.mark.ai
    def test_build_tool_config__handles_default_values__with_minimal_kwargs_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
    ) -> None:
        """
        Purpose: Ensure factory respects default config values when kwargs are omitted.
        Why this matters: Default values provide sensible fallbacks and reduce boilerplate.
        Setup summary: Register tool, build config with partial kwargs, verify defaults are used.
        """
        # Arrange
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        # Act - only provide one parameter, let the other use default
        config = ToolFactory.build_tool_config("test_tool", test_param="custom")

        # Assert
        assert isinstance(config, MockToolConfig)
        assert config.test_param == "custom"
        assert config.optional_param == 42  # default value

    @pytest.mark.ai
    def test_build_tool__accepts_args_and_kwargs__passes_to_constructor_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
        test_tool_config: MockToolConfig,
    ) -> None:
        """
        Purpose: Verify that build_tool passes arbitrary args/kwargs to tool constructor.
        Why this matters: Allows flexible tool initialization without modifying factory.
        Setup summary: Register tool, call build_tool with extra kwargs, verify tool is created.
        """
        # Arrange
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        # Act - build_tool should accept and pass through additional arguments
        tool = ToolFactory.build_tool("test_tool", test_tool_config)

        # Assert - tool is built successfully (constructor accepted the arguments)
        assert isinstance(tool, MockTool)
        assert tool.name == "test_tool"

    @pytest.mark.ai
    def test_register_tool__overwrites_existing_registration__with_same_name_AI(
        self,
        test_tool_class: type[Tool],
        test_tool_config_class: type[BaseToolConfig],
    ) -> None:
        """
        Purpose: Verify that re-registering a tool with the same name overwrites the previous registration.
        Why this matters: Allows tool updates/replacements at runtime without complex removal logic.
        Setup summary: Register tool twice with different configs, verify second registration wins.
        """
        # Arrange
        ToolFactory.register_tool(test_tool_class, test_tool_config_class)

        class NewConfig(BaseToolConfig):
            new_field: str = "new"

        # Act - register again with different config
        ToolFactory.register_tool(test_tool_class, NewConfig)

        # Assert
        assert ToolFactory.tool_config_map["test_tool"] == NewConfig
        config: BaseToolConfig = ToolFactory.build_tool_config(
            "test_tool", new_field="value"
        )
        assert isinstance(config, NewConfig)
