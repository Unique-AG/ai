"""
Test suite for ToolBuildConfig class and ToolFactory functionality.

This test demonstrates the complete lifecycle of tool configuration and factory usage:
1. Creating a custom tool and configuration
2. Registering with the factory
3. Testing ToolBuildConfig creation and validation
4. Testing tool building through the factory
5. Cleaning up registered tools
"""

import json
from typing import cast
from unittest.mock import Mock

import pytest
from pydantic import RootModel

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import BaseToolConfig, ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class TestToolConfig(BaseToolConfig):
    """Test configuration for our mock tool."""

    test_param: str = "default_value"
    optional_param: int = 42


class TestTool(Tool[TestToolConfig]):
    """Mock tool for testing purposes."""

    name = "test_tool"

    def __init__(self, configuration: TestToolConfig, *args, **kwargs):
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
        from pydantic import BaseModel

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


class TestToolBuildConfigAndFactory:
    """Test suite for ToolBuildConfig and ToolFactory integration."""

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

    def test_tool_registration_with_factory(self):
        """Test registering a tool and its configuration with the factory."""
        # Register the test tool
        ToolFactory.register_tool(TestTool, TestToolConfig)

        # Verify registration
        assert "test_tool" in ToolFactory.tool_map
        assert "test_tool" in ToolFactory.tool_config_map
        assert ToolFactory.tool_map["test_tool"] == TestTool
        assert ToolFactory.tool_config_map["test_tool"] == TestToolConfig

    def test_tool_build_config_creation_with_dict_configuration(self):
        """Test creating ToolBuildConfig with dictionary configuration.

        Note: is_sub_agent in the dict is used by the validator only when True
        (to set name="SubAgentTool"). Here it's False, so it's ignored.
        is_sub_agent is a computed property: name == "SubAgentTool", hence False.
        """
        # First register the tool
        ToolFactory.register_tool(TestTool, TestToolConfig)

        # Create configuration data
        config_data = {
            "name": "test_tool",
            "configuration": {"test_param": "custom_value", "optional_param": 100},
            "display_name": "Test Tool Display",
            "icon": ToolIcon.ANALYTICS,
            "selection_policy": ToolSelectionPolicy.ON_BY_DEFAULT,
            "is_exclusive": True,
            "is_sub_agent": False,  # Ignored; computed from name
            "is_enabled": True,
        }

        # Create ToolBuildConfig
        tool_build_config = ToolBuildConfig(**config_data)

        # Verify configuration
        assert tool_build_config.name == "test_tool"
        assert tool_build_config.display_name == "Test Tool Display"
        assert tool_build_config.icon == ToolIcon.ANALYTICS
        assert tool_build_config.selection_policy == ToolSelectionPolicy.ON_BY_DEFAULT
        assert tool_build_config.is_exclusive is True
        assert (
            tool_build_config.is_sub_agent is False
        )  # Computed: name != "SubAgentTool"
        assert tool_build_config.is_enabled is True

        # Verify configuration object
        assert isinstance(tool_build_config.configuration, TestToolConfig)
        assert tool_build_config.configuration.test_param == "custom_value"
        assert tool_build_config.configuration.optional_param == 100

    def test_tool_build_config_creation_with_pre_instantiated_configuration(self):
        """Test creating ToolBuildConfig with pre-instantiated configuration object.

        is_sub_agent is computed from name; for name="test_tool" it is False.
        """
        # First register the tool
        ToolFactory.register_tool(TestTool, TestToolConfig)

        # Create configuration object directly
        config_obj = TestToolConfig(test_param="direct_value", optional_param=200)

        # Create configuration data
        config_data = {
            "name": "test_tool",
            "configuration": config_obj,
            "display_name": "Direct Config Tool",
            "icon": ToolIcon.BOOK,
            "selection_policy": ToolSelectionPolicy.BY_USER,
            "is_exclusive": False,
            "is_sub_agent": False,  # Ignored; computed from name
            "is_enabled": False,
        }

        # Create ToolBuildConfig
        tool_build_config = ToolBuildConfig(**config_data)

        # Verify configuration
        assert tool_build_config.name == "test_tool"
        assert tool_build_config.display_name == "Direct Config Tool"
        assert tool_build_config.icon == ToolIcon.BOOK
        assert tool_build_config.selection_policy == ToolSelectionPolicy.BY_USER
        assert tool_build_config.is_exclusive is False
        assert (
            tool_build_config.is_sub_agent is False
        )  # Computed: name != "SubAgentTool"
        assert tool_build_config.is_enabled is False

        # Verify configuration object
        assert tool_build_config.configuration is config_obj
        config = tool_build_config.configuration
        assert isinstance(config, TestToolConfig)
        assert config.test_param == "direct_value"
        assert config.optional_param == 200

    def test_tool_build_config_defaults(self):
        """Test ToolBuildConfig with default values.

        is_sub_agent defaults to False for non-SubAgentTool names (computed property).
        """
        # First register the tool
        ToolFactory.register_tool(TestTool, TestToolConfig)

        # Create minimal configuration
        config_data = {
            "name": "test_tool",
            "configuration": {"test_param": "default_test"},
        }

        # Create ToolBuildConfig
        tool_build_config = ToolBuildConfig(**config_data)

        # Verify defaults
        assert tool_build_config.display_name == ""
        assert tool_build_config.icon == ToolIcon.BOOK
        assert tool_build_config.selection_policy == ToolSelectionPolicy.BY_USER
        assert tool_build_config.is_exclusive is False
        assert (
            tool_build_config.is_sub_agent is False
        )  # Computed: name != "SubAgentTool"
        assert tool_build_config.is_enabled is True

    def test_tool_factory_build_tool_config(self):
        """Test building tool configuration through factory."""
        # Register the tool
        ToolFactory.register_tool(TestTool, TestToolConfig)

        # Build configuration through factory
        config = ToolFactory.build_tool_config(
            "test_tool", test_param="factory_built", optional_param=300
        )

        # Verify configuration
        assert isinstance(config, TestToolConfig)
        assert config.test_param == "factory_built"
        assert config.optional_param == 300

    def test_tool_factory_build_tool(self):
        """Test building tool instance through factory."""
        # Register the tool
        ToolFactory.register_tool(TestTool, TestToolConfig)

        # Create configuration
        config = TestToolConfig(test_param="tool_test", optional_param=400)

        # Build tool through factory
        tool = ToolFactory.build_tool("test_tool", config)

        # Verify tool
        assert isinstance(tool, TestTool)
        assert tool.configuration == config
        assert tool.name == "test_tool"

    def test_tool_factory_build_tool_with_settings(self):
        """Test building tool with settings through factory.

        is_sub_agent in ToolBuildConfig is a computed property; passing it is
        ignored. For name="test_tool" it evaluates to False.
        """
        # Register the tool
        ToolFactory.register_tool(TestTool, TestToolConfig)

        # Create configuration and settings
        config = TestToolConfig(test_param="settings_test", optional_param=500)
        settings = ToolBuildConfig(
            name="test_tool",
            configuration=config,
            display_name="Settings Test Tool",
            icon=ToolIcon.INTEGRATION,
            selection_policy=ToolSelectionPolicy.FORCED_BY_DEFAULT,
            is_exclusive=True,
            is_enabled=True,
        )

        # Build tool with settings
        tool = ToolFactory.build_tool_with_settings("test_tool", settings, config)

        # Verify tool and settings
        assert isinstance(tool, TestTool)
        assert tool.configuration == config
        assert tool.settings == settings
        assert tool.display_name() == "Settings Test Tool"
        assert tool.icon() == ToolIcon.INTEGRATION
        assert tool.selection_policy() == ToolSelectionPolicy.FORCED_BY_DEFAULT
        assert tool.is_exclusive() is True
        assert tool.is_enabled() is True

    def test_tool_factory_error_handling(self):
        """Test error handling in tool factory."""
        # Test building unregistered tool
        with pytest.raises(ValueError, match="Tool unregistered_tool not found"):
            ToolFactory.build_tool_config("unregistered_tool", test_param="test")

        with pytest.raises(KeyError):
            ToolFactory.build_tool("unregistered_tool", None)

    def test_tool_build_config_validation_with_unregistered_tool(self):
        """Test ToolBuildConfig validation with unregistered tool."""
        # Try to create config for unregistered tool
        config_data = {
            "name": "unregistered_tool",
            "configuration": {"test_param": "test"},
        }

        # This should raise an error during validation
        with pytest.raises((ValueError, KeyError)):
            ToolBuildConfig(**config_data)

    def test_tool_build_config_with_invalid_configuration_type(self):
        """Test ToolBuildConfig with invalid configuration type."""
        # Register the tool
        ToolFactory.register_tool(TestTool, TestToolConfig)

        # Create config with wrong configuration type
        config_data = {
            "name": "test_tool",
            "configuration": "invalid_config_type",  # Should be dict or TestToolConfig
        }

        # This should raise an error during validation
        with pytest.raises((TypeError, ValueError, AssertionError)):
            ToolBuildConfig(**config_data)

    def test_tool_build_config_model_rebuild(self):
        """Test model rebuild functionality."""

        # Verify the model is still functional
        ToolFactory.register_tool(TestTool, TestToolConfig)

        config_data = {
            "name": "test_tool",
            "configuration": {"test_param": "rebuild_test"},
        }

        tool_build_config = ToolBuildConfig(**config_data)
        assert tool_build_config.name == "test_tool"
        assert isinstance(tool_build_config.configuration, TestToolConfig)

    def test_complete_tool_lifecycle(self):
        """Test complete tool lifecycle: register, configure, build, use, cleanup.

        is_sub_agent is computed from name; omitted or False yields False.
        """
        # Step 1: Register tool with factory
        ToolFactory.register_tool(TestTool, TestToolConfig)

        config = TestToolConfig(test_param="lifecycle_test", optional_param=600)
        # Step 2: Create tool build configuration
        tool_build_config = ToolBuildConfig(
            name="test_tool",
            configuration=config,
            display_name="Lifecycle Test Tool",
            icon=ToolIcon.TELESCOPE,
            selection_policy=ToolSelectionPolicy.ON_BY_DEFAULT,
            is_exclusive=False,
            is_enabled=True,
        )

        # Step 3: Build tool with settings
        tool = ToolFactory.build_tool_with_settings(
            "test_tool", tool_build_config, tool_build_config.configuration
        )

        # Step 4: Verify tool functionality
        assert tool.name == "test_tool"
        assert tool.display_name() == "Lifecycle Test Tool"
        assert tool.icon() == ToolIcon.TELESCOPE
        assert tool.selection_policy() == ToolSelectionPolicy.ON_BY_DEFAULT
        assert tool.is_exclusive() is False
        assert tool.is_enabled() is True

        # Step 5: Test tool description
        description = tool.tool_description()
        assert description.name == "test_tool"
        assert description.description == "A test tool for unit testing"

        # Step 6: Verify configuration
        config = cast(TestToolConfig, tool.configuration)
        assert isinstance(config, TestToolConfig)
        assert config.test_param == "lifecycle_test"
        assert config.optional_param == 600

        # Step 7: Cleanup (handled by teardown_method)
        # The teardown method will restore the original factory state

    def test_multiple_tool_registration_and_cleanup(self):
        """Test registering multiple tools and proper cleanup."""

        # Create additional test tools
        class AnotherTestToolConfig(BaseToolConfig):
            another_param: str = "another_default"

        class AnotherTestTool(Tool[AnotherTestToolConfig]):
            name = "another_test_tool"

            def __init__(self, configuration: AnotherTestToolConfig, *args, **kwargs):
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
                self.settings = ToolBuildConfig(
                    name=self.name, configuration=configuration
                )

            @property
            def tool_description(self) -> LanguageModelToolDescription:
                from pydantic import BaseModel

                class AnotherTestParameters(BaseModel):
                    another_param: str

                return LanguageModelToolDescription(
                    name=self.name,
                    description="Another test tool",
                    parameters=AnotherTestParameters,
                )

            async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
                """Mock implementation of the run method."""
                return ToolCallResponse(
                    id=tool_call.id or "another_test_id",
                    name=tool_call.name,
                    content="Another test tool response",
                    debug_info={"test": "another_debug_info"},
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

        # Register multiple tools
        ToolFactory.register_tool(TestTool, TestToolConfig)
        ToolFactory.register_tool(AnotherTestTool, AnotherTestToolConfig)

        # Verify both are registered
        assert "test_tool" in ToolFactory.tool_map
        assert "another_test_tool" in ToolFactory.tool_map
        assert len(ToolFactory.tool_map) == 2

        # Test building both tools
        tool1 = ToolFactory.build_tool("test_tool", TestToolConfig())
        tool2 = ToolFactory.build_tool("another_test_tool", AnotherTestToolConfig())

        assert isinstance(tool1, TestTool)
        assert isinstance(tool2, AnotherTestTool)

        # Cleanup is handled by teardown_method
        # This test verifies that multiple registrations work correctly

    def test_tool_build_config_model_dump(self) -> None:
        ToolFactory.register_tool(TestTool, TestToolConfig)
        config = TestToolConfig()

        tool_build_config = ToolBuildConfig(name="test_tool", configuration=config)
        assert tool_build_config.model_dump()["configuration"] == config.model_dump()
        assert json.loads(tool_build_config.model_dump_json())[
            "configuration"
        ] == json.loads(config.model_dump_json())

    def test_tool_build_config_model_dump_composite(self) -> None:
        ToolFactory.register_tool(TestTool, TestToolConfig)
        config = TestToolConfig()
        tool_build_config_list = RootModel(list[ToolBuildConfig]).model_validate(
            [
                ToolBuildConfig(name="test_tool", configuration=config),
            ]
        )

        assert (
            tool_build_config_list.model_dump()[0]["configuration"]
            == config.model_dump()
        )
        assert (
            json.loads(tool_build_config_list.model_dump_json())[0]["configuration"]
            == config.model_dump()
        )
