"""
Tests for unique_toolkit.agentic.tools.config module.

This module tests the configuration components for tools including:
- ToolIcon enum
- ToolSelectionPolicy enum
- handle_undefined_icon validator function
- ToolBuildConfig model with validation and serialization
"""

import json
from typing import Any

import pytest
from pydantic import BaseModel

from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
    handle_undefined_icon,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


# Test fixtures for config testing
class SimpleToolConfig(BaseToolConfig):
    """Simple tool configuration for testing."""

    param_one: str = "default"
    param_two: int = 100


@pytest.fixture
def simple_config() -> SimpleToolConfig:
    """
    Base fixture for simple tool configuration.

    Returns:
        SimpleToolConfig with default values.
    """
    return SimpleToolConfig(param_one="test", param_two=200)


@pytest.fixture
def simple_config_dict() -> dict[str, Any]:
    """
    Base fixture for simple tool configuration as dict.

    Returns:
        Dictionary representation of tool configuration.
    """
    return {"param_one": "test", "param_two": 200}


@pytest.fixture(autouse=True, scope="module")
def clean_factory_state():
    """
    Autouse fixture to ensure ToolFactory is completely clean before and after this test module.

    This prevents test pollution from affecting other test modules.
    Runs once per module.
    """
    # Clean state before module tests start
    ToolFactory.tool_map.clear()
    ToolFactory.tool_config_map.clear()

    yield

    # After all tests in module complete, clean up thoroughly again
    ToolFactory.tool_map.clear()
    ToolFactory.tool_config_map.clear()


@pytest.fixture
def register_simple_tool():
    """
    Fixture to register and cleanup SimpleToolConfig in ToolFactory.

    This fixture registers a dummy tool with the factory so that
    ToolBuildConfig validation can succeed, then cleans up after the test.
    """
    # Store original state
    original_tool_map = ToolFactory.tool_map.copy()
    original_config_map = ToolFactory.tool_config_map.copy()

    # Register dummy tool names used in tests
    test_tool_names = [
        "test_tool",
        "full_test_tool",
        "serialize_test",
        "config_fields_test",
        "json_test",
        "json_config_test",
        "round_trip_test",
        "icon_test_analytics",
        "icon_test_book",
        "icon_test_folderdata",
        "icon_test_integration",
        "icon_test_text_compare",
        "icon_test_world",
        "icon_test_quick_reply",
        "icon_test_chat_plus",
        "icon_test_telescope",
        "policy_test_forced_by_default",
        "policy_test_on_by_default",
        "policy_test_by_user",
    ]

    for tool_name in test_tool_names:
        ToolFactory.tool_config_map[tool_name] = SimpleToolConfig

    yield

    # Cleanup - remove all tools we registered
    for tool_name in test_tool_names:
        ToolFactory.tool_map.pop(tool_name, None)
        ToolFactory.tool_config_map.pop(tool_name, None)

    # Also remove any other tools that might have been registered during tests
    ToolFactory.tool_map.pop("extended_tool", None)
    ToolFactory.tool_config_map.pop("extended_tool", None)
    ToolFactory.tool_map.pop("detailed_tool", None)
    ToolFactory.tool_config_map.pop("detailed_tool", None)

    # Finally restore original state (in case tests need pre-existing tools)
    ToolFactory.tool_map.update(original_tool_map)
    ToolFactory.tool_config_map.update(original_config_map)


# ============================================================================
# ToolIcon Tests
# ============================================================================


@pytest.mark.ai
def test_tool_icon__has_all_expected_values__enum_definition() -> None:
    """
    Purpose: Verify ToolIcon enum contains all expected icon values.
    Why this matters: Ensures UI has all valid icon options available.
    Setup summary: Access enum values and assert expected names exist.
    """
    # Arrange & Act
    icon_values = [icon.value for icon in ToolIcon]

    # Assert
    assert "IconAnalytics" in icon_values
    assert "IconBook" in icon_values
    assert "IconFolderData" in icon_values
    assert "IconIntegration" in icon_values
    assert "IconTextCompare" in icon_values
    assert "IconWorld" in icon_values
    assert "IconQuickReply" in icon_values
    assert "IconChatPlus" in icon_values
    assert "IconTelescope" in icon_values


@pytest.mark.ai
def test_tool_icon__can_be_instantiated__from_string() -> None:
    """
    Purpose: Verify ToolIcon can be created from string value.
    Why this matters: Enables deserialization from JSON/dict configurations.
    Setup summary: Create enum from string value and assert equality.
    """
    # Arrange
    icon_str = "IconAnalytics"

    # Act
    icon = ToolIcon(icon_str)

    # Assert
    assert icon == ToolIcon.ANALYTICS
    assert icon.value == "IconAnalytics"


@pytest.mark.ai
def test_tool_icon__compares_correctly__with_string() -> None:
    """
    Purpose: Verify ToolIcon enum can be compared with string values.
    Why this matters: Simplifies comparisons in application code.
    Setup summary: Compare enum instance with string value.
    """
    # Arrange
    icon = ToolIcon.BOOK

    # Act & Assert
    assert icon == "IconBook"
    assert icon.value == "IconBook"


# ============================================================================
# ToolSelectionPolicy Tests
# ============================================================================


@pytest.mark.ai
def test_tool_selection_policy__has_all_expected_values__enum_definition() -> None:
    """
    Purpose: Verify ToolSelectionPolicy enum contains all expected policy values.
    Why this matters: Ensures tool selection behavior is properly configured.
    Setup summary: Access enum values and assert expected names exist.
    """
    # Arrange & Act
    policy_values = [policy.value for policy in ToolSelectionPolicy]

    # Assert
    assert "ForcedByDefault" in policy_values
    assert "OnByDefault" in policy_values
    assert "ByUser" in policy_values


@pytest.mark.ai
def test_tool_selection_policy__can_be_instantiated__from_string() -> None:
    """
    Purpose: Verify ToolSelectionPolicy can be created from string value.
    Why this matters: Enables deserialization from JSON/dict configurations.
    Setup summary: Create enum from string value and assert equality.
    """
    # Arrange
    policy_str = "OnByDefault"

    # Act
    policy = ToolSelectionPolicy(policy_str)

    # Assert
    assert policy == ToolSelectionPolicy.ON_BY_DEFAULT
    assert policy.value == "OnByDefault"


# ============================================================================
# handle_undefined_icon Tests
# ============================================================================


@pytest.mark.ai
def test_handle_undefined_icon__returns_icon__with_valid_string() -> None:
    """
    Purpose: Verify handle_undefined_icon returns correct icon for valid string.
    Why this matters: Ensures valid icon strings are properly converted.
    Setup summary: Pass valid icon string and assert correct enum returned.
    """
    # Arrange
    valid_icon = "IconAnalytics"

    # Act
    result = handle_undefined_icon(valid_icon)

    # Assert
    assert result == ToolIcon.ANALYTICS
    assert isinstance(result, ToolIcon)


@pytest.mark.ai
def test_handle_undefined_icon__returns_book__with_invalid_string() -> None:
    """
    Purpose: Verify handle_undefined_icon returns BOOK icon for invalid string.
    Why this matters: Provides safe fallback for unknown icon values.
    Setup summary: Pass invalid icon string and assert BOOK icon returned.
    """
    # Arrange
    invalid_icon = "InvalidIconName"

    # Act
    result = handle_undefined_icon(invalid_icon)

    # Assert
    assert result == ToolIcon.BOOK
    assert isinstance(result, ToolIcon)


@pytest.mark.ai
def test_handle_undefined_icon__returns_book__with_non_string() -> None:
    """
    Purpose: Verify handle_undefined_icon returns BOOK icon for non-string input.
    Why this matters: Handles unexpected input types gracefully.
    Setup summary: Pass non-string value and assert BOOK icon returned.
    """
    # Arrange
    non_string_value = 123

    # Act
    result = handle_undefined_icon(non_string_value)

    # Assert
    assert result == ToolIcon.BOOK
    assert isinstance(result, ToolIcon)


@pytest.mark.ai
def test_handle_undefined_icon__returns_book__with_empty_string() -> None:
    """
    Purpose: Verify handle_undefined_icon returns BOOK icon for empty string.
    Why this matters: Handles edge case of empty string input.
    Setup summary: Pass empty string and assert BOOK icon returned.
    """
    # Arrange
    empty_string = ""

    # Act
    result = handle_undefined_icon(empty_string)

    # Assert
    assert result == ToolIcon.BOOK


@pytest.mark.ai
def test_handle_undefined_icon__returns_book__with_none() -> None:
    """
    Purpose: Verify handle_undefined_icon returns BOOK icon for None.
    Why this matters: Handles missing icon values gracefully.
    Setup summary: Pass None and assert BOOK icon returned.
    """
    # Arrange
    none_value = None

    # Act
    result = handle_undefined_icon(none_value)

    # Assert
    assert result == ToolIcon.BOOK


@pytest.mark.ai
def test_handle_undefined_icon__returns_icon__with_toolicon_enum() -> None:
    """
    Purpose: Verify handle_undefined_icon handles ToolIcon enum input.
    Why this matters: Ensures idempotent behavior when icon already correct type.
    Setup summary: Pass ToolIcon enum and assert same enum returned.
    """
    # Arrange
    icon_enum = ToolIcon.TELESCOPE

    # Act
    result = handle_undefined_icon(icon_enum)

    # Assert
    assert result == ToolIcon.TELESCOPE
    assert isinstance(result, ToolIcon)


# ============================================================================
# ToolBuildConfig Field Tests
# ============================================================================


@pytest.mark.ai
def test_tool_build_config__has_correct_defaults__minimal_input(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify ToolBuildConfig applies correct default values.
    Why this matters: Ensures sensible defaults for optional configuration.
    Setup summary: Create config with minimal fields and assert defaults.
    """
    # Arrange & Act
    config = ToolBuildConfig(name="test_tool", configuration=simple_config)

    # Assert
    assert config.name == "test_tool"
    assert config.configuration == simple_config
    assert config.display_name == ""
    assert config.icon == ToolIcon.BOOK
    assert config.selection_policy == ToolSelectionPolicy.BY_USER
    assert config.is_exclusive is False
    assert config.is_sub_agent is False
    assert config.is_enabled is True


@pytest.mark.ai
def test_tool_build_config__stores_all_fields__with_full_input(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify ToolBuildConfig stores all provided field values.
    Why this matters: Ensures no data loss during configuration creation.
    Setup summary: Create config with all fields and assert values stored.
    """
    # Arrange & Act
    config = ToolBuildConfig(
        name="full_test_tool",
        configuration=simple_config,
        display_name="Full Test Tool",
        icon=ToolIcon.ANALYTICS,
        selection_policy=ToolSelectionPolicy.FORCED_BY_DEFAULT,
        is_exclusive=True,
        is_sub_agent=False,
        is_enabled=False,
    )

    # Assert
    assert config.name == "full_test_tool"
    assert config.configuration == simple_config
    assert config.display_name == "Full Test Tool"
    assert config.icon == ToolIcon.ANALYTICS
    assert config.selection_policy == ToolSelectionPolicy.FORCED_BY_DEFAULT
    assert config.is_exclusive is True
    assert config.is_sub_agent is False
    assert config.is_enabled is False


@pytest.mark.ai
def test_tool_build_config__handles_icon_validation__with_valid_string(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify ToolBuildConfig validates and converts valid icon strings.
    Why this matters: Enables JSON deserialization of icon values.
    Setup summary: Create config with string icon value and assert enum conversion.
    """
    # Arrange
    config_data = {
        "name": "test_tool",
        "configuration": simple_config,
        "icon": "IconIntegration",
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.icon == ToolIcon.INTEGRATION
    assert isinstance(config.icon, ToolIcon)


@pytest.mark.ai
def test_tool_build_config__uses_default_icon__with_invalid_string(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify ToolBuildConfig falls back to BOOK icon for invalid strings.
    Why this matters: Provides resilient handling of bad icon data.
    Setup summary: Create config with invalid icon string and assert BOOK icon.
    """
    # Arrange
    config_data = {
        "name": "test_tool",
        "configuration": simple_config,
        "icon": "InvalidIcon",
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.icon == ToolIcon.BOOK


@pytest.mark.ai
def test_tool_build_config__accepts_selection_policy__from_string(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify ToolBuildConfig accepts selection policy as string.
    Why this matters: Enables JSON deserialization of selection policy.
    Setup summary: Create config with string policy value and assert enum conversion.
    """
    # Arrange
    config_data = {
        "name": "test_tool",
        "configuration": simple_config,
        "selection_policy": "OnByDefault",
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.selection_policy == ToolSelectionPolicy.ON_BY_DEFAULT
    assert isinstance(config.selection_policy, ToolSelectionPolicy)


# ============================================================================
# ToolBuildConfig Validator Tests (initialize_config_based_on_tool_name)
# ============================================================================


@pytest.mark.ai
def test_tool_build_config__validates_dict_config__with_registered_tool(
    test_tool_class,
    test_tool_config_class,
    simple_config_dict: dict[str, Any],
) -> None:
    """
    Purpose: Verify validator converts dict configuration using ToolFactory.
    Why this matters: Enables dynamic tool configuration from JSON/dicts.
    Setup summary: Register tool, create config with dict, assert conversion.
    """
    # Arrange
    ToolFactory.register_tool(test_tool_class, test_tool_config_class)
    config_data = {
        "name": "test_tool",
        "configuration": {"test_param": "validator_test", "optional_param": 999},
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert isinstance(config.configuration, BaseToolConfig)
    assert config.configuration.test_param == "validator_test"
    assert config.configuration.optional_param == 999

    # Cleanup
    ToolFactory.tool_map.pop("test_tool", None)
    ToolFactory.tool_config_map.pop("test_tool", None)


@pytest.mark.ai
def test_tool_build_config__preserves_config_object__when_provided(
    test_tool_class,
    test_tool_config_class,
) -> None:
    """
    Purpose: Verify validator preserves pre-instantiated configuration objects.
    Why this matters: Allows direct configuration object usage without re-validation.
    Setup summary: Register tool, create config with object, assert preserved.
    """
    # Arrange
    ToolFactory.register_tool(test_tool_class, test_tool_config_class)
    from tests.agentic.tools.tool_fixtures import MockToolConfig

    config_obj = MockToolConfig(test_param="preserved", optional_param=777)
    config_data = {"name": "test_tool", "configuration": config_obj}

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.configuration is config_obj
    assert config.configuration.test_param == "preserved"
    assert config.configuration.optional_param == 777

    # Cleanup
    ToolFactory.tool_map.pop("test_tool", None)
    ToolFactory.tool_config_map.pop("test_tool", None)


@pytest.mark.ai
def test_tool_build_config__handles_mcp_tool__with_mcp_source_id() -> None:
    """
    Purpose: Verify validator handles MCP tools with mcp_source_id.
    Why this matters: MCP tools require special handling to skip factory validation.
    Setup summary: Create config with mcp_source_id and assert no factory validation.
    """
    # Arrange
    config_data = {
        "name": "mcp_test_tool",
        "mcp_source_id": "mcp-server-123",
        "configuration": {
            "server_id": "server-123",
            "server_name": "Test Server",
            "mcp_source_id": "mcp-server-123",
        },
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.name == "mcp_test_tool"
    # Configuration should be preserved as dict since MCP tools skip factory validation
    assert isinstance(config.configuration, BaseToolConfig)


@pytest.mark.ai
def test_tool_build_config__handles_sub_agent_tool__with_is_sub_agent_flag() -> None:
    """
    Purpose: Verify validator handles sub-agent tools with is_sub_agent flag.
    Why this matters: Sub-agent tools require ExtendedSubAgentToolConfig.
    Setup summary: Create config with is_sub_agent=True and assert config type.
    """
    # Arrange
    config_data = {
        "name": "sub_agent_test_tool",
        "is_sub_agent": True,
        "configuration": {
            "agent_name": "test_agent",
            "agent_description": "Test sub-agent",
            "system_prompt": "You are a test agent",
        },
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.name == "sub_agent_test_tool"
    assert config.is_sub_agent is True
    # Configuration should be validated as ExtendedSubAgentToolConfig
    from unique_toolkit.agentic.tools.a2a import ExtendedSubAgentToolConfig

    assert isinstance(config.configuration, ExtendedSubAgentToolConfig)


@pytest.mark.ai
def test_tool_build_config__handles_sub_agent_tool__with_camel_case_flag() -> None:
    """
    Purpose: Verify validator handles sub-agent tools with isSubAgent camelCase flag.
    Why this matters: Supports both naming conventions for backward compatibility.
    Setup summary: Create config with isSubAgent=True and assert config type.
    """
    # Arrange
    config_data = {
        "name": "sub_agent_camel_test_tool",
        "isSubAgent": True,
        "configuration": {
            "agent_name": "test_agent",
            "agent_description": "Test sub-agent",
            "system_prompt": "You are a test agent",
        },
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.name == "sub_agent_camel_test_tool"
    assert config.is_sub_agent is True
    from unique_toolkit.agentic.tools.a2a import ExtendedSubAgentToolConfig

    assert isinstance(config.configuration, ExtendedSubAgentToolConfig)


@pytest.mark.ai
def test_tool_build_config__validates_config_type__with_wrong_type(
    test_tool_class,
    test_tool_config_class,
) -> None:
    """
    Purpose: Verify validator demotes the tool when config type doesn't match.
    Why this matters: Ensures type safety between tool and configuration while
    keeping invalid tools from crashing the load (graceful degradation).
    Setup summary: Register tool, provide wrong config type, assert demotion.
    """
    # Arrange
    ToolFactory.register_tool(test_tool_class, test_tool_config_class)

    class WrongConfig(BaseToolConfig):
        wrong_param: str = "wrong"

    wrong_config = WrongConfig()
    config_data = {"name": "test_tool", "configuration": wrong_config}

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert: invalid config type demotes the tool to disabled
    assert config.is_enabled is False
    assert isinstance(config.configuration, BaseToolConfig)

    # Cleanup
    ToolFactory.tool_map.pop("test_tool", None)
    ToolFactory.tool_config_map.pop("test_tool", None)


@pytest.mark.ai
def test_tool_build_config__skips_validation__with_non_dict_value() -> None:
    """
    Purpose: Verify validator skips processing when value is not a dict.
    Why this matters: Handles edge cases in validation pipeline gracefully.
    Setup summary: Pass non-dict value to validator and assert early return.
    """
    # Arrange
    non_dict_value = "not_a_dict"

    # Act
    from unique_toolkit.agentic.tools.config import ToolBuildConfig

    result = ToolBuildConfig.initialize_config_based_on_tool_name(non_dict_value, None)

    # Assert
    assert result == non_dict_value


# ============================================================================
# ToolBuildConfig Serialization Tests (model_dump)
# ============================================================================


@pytest.mark.ai
def test_tool_build_config__serializes_to_dict__with_model_dump(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify model_dump serializes ToolBuildConfig to dict correctly.
    Why this matters: Enables conversion to JSON-compatible format.
    Setup summary: Create config, call model_dump, assert dict structure.
    """
    # Arrange
    config = ToolBuildConfig(
        name="serialize_test",
        configuration=simple_config,
        display_name="Serialize Test",
        icon=ToolIcon.WORLD,
        selection_policy=ToolSelectionPolicy.ON_BY_DEFAULT,
        is_exclusive=True,
        is_sub_agent=False,
        is_enabled=True,
    )

    # Act
    result = config.model_dump()

    # Assert
    assert isinstance(result, dict)
    assert result["name"] == "serialize_test"
    assert result["display_name"] == "Serialize Test"
    assert result["icon"] == ToolIcon.WORLD
    assert result["selection_policy"] == ToolSelectionPolicy.ON_BY_DEFAULT
    assert result["is_exclusive"] is True
    assert result["is_sub_agent"] is False
    assert result["is_enabled"] is True
    assert isinstance(result["configuration"], dict)


@pytest.mark.ai
def test_tool_build_config__preserves_config_fields__in_model_dump(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify model_dump includes all configuration subclass fields.
    Why this matters: Prevents data loss during serialization of subclasses.
    Setup summary: Create config, call model_dump, assert config fields present.
    """
    # Arrange
    config = ToolBuildConfig(name="config_fields_test", configuration=simple_config)

    # Act
    result = config.model_dump()

    # Assert
    assert "configuration" in result
    assert isinstance(result["configuration"], dict)
    assert result["configuration"]["param_one"] == "test"
    assert result["configuration"]["param_two"] == 200


# ============================================================================
# ToolBuildConfig Serialization Tests (model_dump_json)
# ============================================================================


@pytest.mark.ai
def test_tool_build_config__serializes_to_json__with_model_dump_json(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify model_dump_json serializes ToolBuildConfig to JSON string.
    Why this matters: Enables storage and transmission of configuration.
    Setup summary: Create config, call model_dump_json, assert valid JSON.
    """
    # Arrange
    config = ToolBuildConfig(
        name="json_test",
        configuration=simple_config,
        display_name="JSON Test",
        icon=ToolIcon.QUICK_REPLY,
        selection_policy=ToolSelectionPolicy.FORCED_BY_DEFAULT,
        is_exclusive=False,
        is_sub_agent=False,
        is_enabled=True,
    )

    # Act
    result = config.model_dump_json()

    # Assert
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert parsed["name"] == "json_test"
    assert parsed["display_name"] == "JSON Test"
    assert parsed["icon"] == "IconQuickReply"
    assert parsed["selection_policy"] == "ForcedByDefault"
    assert parsed["is_exclusive"] is False
    assert parsed["is_sub_agent"] is False
    assert parsed["is_enabled"] is True


@pytest.mark.ai
def test_tool_build_config__includes_config_fields__in_model_dump_json(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify model_dump_json includes configuration subclass fields.
    Why this matters: Ensures complete serialization of configuration data.
    Setup summary: Create config, call model_dump_json, parse and assert fields.
    """
    # Arrange
    config = ToolBuildConfig(name="json_config_test", configuration=simple_config)

    # Act
    result = config.model_dump_json()
    parsed = json.loads(result)

    # Assert
    assert "configuration" in parsed
    assert isinstance(parsed["configuration"], dict)
    assert parsed["configuration"]["param_one"] == "test"
    assert parsed["configuration"]["param_two"] == 200


@pytest.mark.ai
def test_tool_build_config__round_trip_serialization__preserves_data(
    simple_config: SimpleToolConfig,
    register_simple_tool,
) -> None:
    """
    Purpose: Verify round-trip JSON serialization preserves all data.
    Why this matters: Ensures configuration can be stored and restored without loss.
    Setup summary: Serialize to JSON, parse, create new config, assert equality.
    """
    # Arrange
    original_config = ToolBuildConfig(
        name="round_trip_test",
        configuration=simple_config,
        display_name="Round Trip",
        icon=ToolIcon.CHAT_PLUS,
        selection_policy=ToolSelectionPolicy.ON_BY_DEFAULT,
        is_exclusive=True,
        is_sub_agent=False,
        is_enabled=False,
    )

    # Act
    json_str = original_config.model_dump_json()
    parsed_data = json.loads(json_str)

    # Restore configuration
    parsed_data["configuration"] = SimpleToolConfig(**parsed_data["configuration"])
    restored_config = ToolBuildConfig(**parsed_data)

    # Assert
    assert restored_config.name == original_config.name
    assert restored_config.display_name == original_config.display_name
    assert restored_config.icon == original_config.icon
    assert restored_config.selection_policy == original_config.selection_policy
    assert restored_config.is_exclusive == original_config.is_exclusive
    assert restored_config.is_sub_agent == original_config.is_sub_agent
    assert restored_config.is_enabled == original_config.is_enabled
    assert restored_config.configuration.param_one == simple_config.param_one
    assert restored_config.configuration.param_two == simple_config.param_two


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.ai
def test_tool_build_config__handles_all_icon_types__in_serialization(
    register_simple_tool,
) -> None:
    """
    Purpose: Verify all ToolIcon enum values can be serialized and deserialized.
    Why this matters: Ensures complete icon support in configuration system.
    Setup summary: Test each icon through serialization round-trip.
    """
    # Arrange
    icons = [
        ToolIcon.ANALYTICS,
        ToolIcon.BOOK,
        ToolIcon.FOLDERDATA,
        ToolIcon.INTEGRATION,
        ToolIcon.TEXT_COMPARE,
        ToolIcon.WORLD,
        ToolIcon.QUICK_REPLY,
        ToolIcon.CHAT_PLUS,
        ToolIcon.TELESCOPE,
    ]
    config_obj = SimpleToolConfig()

    for icon in icons:
        # Act
        config = ToolBuildConfig(
            name=f"icon_test_{icon.name.lower()}",
            configuration=config_obj,
            icon=icon,
        )
        json_str = config.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["icon"] == icon.value

        # Restore and verify
        restored_config = ToolBuildConfig(
            name=parsed["name"],
            configuration=config_obj,
            icon=parsed["icon"],
        )
        assert restored_config.icon == icon


@pytest.mark.ai
def test_tool_build_config__handles_all_selection_policies__in_serialization(
    register_simple_tool,
) -> None:
    """
    Purpose: Verify all ToolSelectionPolicy values serialize correctly.
    Why this matters: Ensures complete policy support in configuration system.
    Setup summary: Test each policy through serialization round-trip.
    """
    # Arrange
    policies = [
        ToolSelectionPolicy.FORCED_BY_DEFAULT,
        ToolSelectionPolicy.ON_BY_DEFAULT,
        ToolSelectionPolicy.BY_USER,
    ]
    config_obj = SimpleToolConfig()

    for policy in policies:
        # Act
        config = ToolBuildConfig(
            name=f"policy_test_{policy.name.lower()}",
            configuration=config_obj,
            selection_policy=policy,
        )
        json_str = config.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["selection_policy"] == policy.value

        # Restore and verify
        restored_config = ToolBuildConfig(
            name=parsed["name"],
            configuration=config_obj,
            selection_policy=parsed["selection_policy"],
        )
        assert restored_config.selection_policy == policy


# ============================================================================
# model_serializer Tests - Verifying Polymorphic Serialization
# ============================================================================


@pytest.mark.ai
def test_tool_build_config__serializes_subclass_fields__with_model_serializer(
    register_simple_tool,
) -> None:
    """
    Purpose: Verify model_serializer properly serializes subclass configuration fields.
    Why this matters: Ensures polymorphic serialization works without custom methods.
    Setup summary: Create config with subclass, serialize, assert all fields present.
    """

    # Arrange
    class ExtendedConfig(BaseToolConfig):
        """Extended configuration with additional fields."""

        base_field: str = "base"
        extra_field: int = 999
        another_field: bool = True

    # Register the extended config
    ToolFactory.tool_config_map["extended_tool"] = ExtendedConfig

    extended_config = ExtendedConfig(
        base_field="custom_base", extra_field=12345, another_field=False
    )

    config = ToolBuildConfig(name="extended_tool", configuration=extended_config)

    # Act
    serialized = config.model_dump()

    # Assert - All subclass fields should be present
    assert "configuration" in serialized
    assert isinstance(serialized["configuration"], dict)
    assert serialized["configuration"]["base_field"] == "custom_base"
    assert serialized["configuration"]["extra_field"] == 12345
    assert serialized["configuration"]["another_field"] is False

    # Cleanup
    ToolFactory.tool_config_map.pop("extended_tool", None)


@pytest.mark.ai
def test_tool_build_config__serializes_to_json_with_subclass__using_model_serializer(
    register_simple_tool,
) -> None:
    """
    Purpose: Verify model_dump_json serializes subclass fields correctly.
    Why this matters: Ensures JSON serialization preserves all configuration data.
    Setup summary: Create config, serialize to JSON, parse, assert fields intact.
    """

    # Arrange
    class DetailedConfig(BaseToolConfig):
        """Configuration with various field types."""

        string_field: str = "test"
        int_field: int = 42
        bool_field: bool = True
        list_field: list[str] = ["a", "b", "c"]

    # Register the config
    ToolFactory.tool_config_map["detailed_tool"] = DetailedConfig

    detailed_config = DetailedConfig(
        string_field="custom",
        int_field=100,
        bool_field=False,
        list_field=["x", "y"],
    )

    config = ToolBuildConfig(name="detailed_tool", configuration=detailed_config)

    # Act
    json_str = config.model_dump_json()
    parsed = json.loads(json_str)

    # Assert
    assert parsed["name"] == "detailed_tool"
    assert parsed["configuration"]["string_field"] == "custom"
    assert parsed["configuration"]["int_field"] == 100
    assert parsed["configuration"]["bool_field"] is False
    assert parsed["configuration"]["list_field"] == ["x", "y"]

    # Cleanup
    ToolFactory.tool_config_map.pop("detailed_tool", None)


# ============================================================================
# model_dump kwargs: by_alias, exclude_defaults, exclude_none
# ============================================================================


class _NullableConfig(BaseToolConfig):
    """Config with an optional field to test exclude_none."""

    value: str = "default_value"
    optional_note: str | None = None


class _AnotherConfig(BaseToolConfig):
    """Second config subclass with distinct fields for list heterogeneity tests."""

    threshold: float = 0.5
    label: str = "default_label"
    optional_note: str | None = None


@pytest.mark.ai
def test_tool_build_config__by_alias__camelcases_top_level_fields() -> None:
    """
    Purpose: Verify model_dump(by_alias=True) produces camelCase keys for ToolBuildConfig fields.
    Why this matters: The API layer consumes camelCase JSON; snake_case keys would break it.
    Setup summary: Create config, dump with by_alias=True, assert camelCase keys present.
    """
    ToolFactory.tool_config_map["alias_tool"] = SimpleToolConfig
    try:
        config = ToolBuildConfig(
            name="alias_tool",
            configuration=SimpleToolConfig(param_one="x", param_two=1),
            display_name="Alias Tool",
            selection_policy=ToolSelectionPolicy.ON_BY_DEFAULT,
            is_exclusive=True,
        )

        result = config.model_dump(by_alias=True)

        assert "displayName" in result
        assert "selectionPolicy" in result
        assert "isExclusive" in result
        assert "isSubAgent" in result
        assert "isEnabled" in result
        assert "display_name" not in result
        assert "is_exclusive" not in result
    finally:
        ToolFactory.tool_config_map.pop("alias_tool", None)


@pytest.mark.ai
def test_tool_build_config__by_alias__camelcases_nested_configuration_fields() -> None:
    """
    Purpose: Verify by_alias=True propagates into the nested configuration dict.
    Why this matters: SerializeAsAny must respect dump kwargs end-to-end, not just at the top level.
    Setup summary: Use a subclass with snake_case fields, dump by_alias, assert camelCase in config.
    """
    ToolFactory.tool_config_map["alias_nested_tool"] = _AnotherConfig
    try:
        config = ToolBuildConfig(
            name="alias_nested_tool",
            configuration=_AnotherConfig(
                threshold=0.9, label="custom", optional_note=None
            ),
        )

        result = config.model_dump(by_alias=True)
        cfg = result["configuration"]

        assert "optionalNote" in cfg
        assert "optional_note" not in cfg
    finally:
        ToolFactory.tool_config_map.pop("alias_nested_tool", None)


@pytest.mark.ai
def test_tool_build_config__list_container__by_alias__all_items_camelcased() -> None:
    """
    Purpose: Verify by_alias=True works across all items in a list[ToolBuildConfig] container.
    Why this matters: Tool lists are the primary serialization target; every item must be camelCased.
    Setup summary: Wrap two differently-typed configs in a ToolSet, dump by_alias, assert all keys.
    """

    class ToolSet(BaseModel):
        tools: list[ToolBuildConfig]

    ToolFactory.tool_config_map["list_alias_tool_a"] = SimpleToolConfig
    ToolFactory.tool_config_map["list_alias_tool_b"] = _AnotherConfig
    try:
        tool_set = ToolSet(
            tools=[
                ToolBuildConfig(
                    name="list_alias_tool_a",
                    configuration=SimpleToolConfig(param_one="p", param_two=5),
                    display_name="Tool A",
                ),
                ToolBuildConfig(
                    name="list_alias_tool_b",
                    configuration=_AnotherConfig(threshold=0.7, label="lbl"),
                    is_exclusive=True,
                ),
            ]
        )

        result = tool_set.model_dump(by_alias=True)
        tools = result["tools"]

        assert len(tools) == 2

        t0 = tools[0]
        assert "displayName" in t0
        assert "isExclusive" in t0
        assert "display_name" not in t0
        cfg0 = t0["configuration"]
        assert "paramOne" in cfg0
        assert "paramTwo" in cfg0
        assert "param_one" not in cfg0

        t1 = tools[1]
        assert "isExclusive" in t1
        cfg1 = t1["configuration"]
        assert "optionalNote" in cfg1
        assert "optional_note" not in cfg1
    finally:
        ToolFactory.tool_config_map.pop("list_alias_tool_a", None)
        ToolFactory.tool_config_map.pop("list_alias_tool_b", None)


@pytest.mark.ai
def test_tool_build_config__list_container__heterogeneous_subclasses_serialize_correctly() -> (
    None
):
    """
    Purpose: Verify each item in list[ToolBuildConfig] serializes using its own subclass schema.
    Why this matters: Without SerializeAsAny, all items would be truncated to BaseToolConfig fields.
    Setup summary: Two configs with non-overlapping subclass fields; assert both are fully present.
    """

    class ToolSet(BaseModel):
        tools: list[ToolBuildConfig]

    ToolFactory.tool_config_map["hetero_tool_a"] = SimpleToolConfig
    ToolFactory.tool_config_map["hetero_tool_b"] = _AnotherConfig
    try:
        tool_set = ToolSet(
            tools=[
                ToolBuildConfig(
                    name="hetero_tool_a",
                    configuration=SimpleToolConfig(param_one="hello", param_two=42),
                ),
                ToolBuildConfig(
                    name="hetero_tool_b",
                    configuration=_AnotherConfig(threshold=0.8, label="my_label"),
                ),
            ]
        )

        result = tool_set.model_dump()
        tools = result["tools"]

        assert len(tools) == 2
        assert tools[0]["configuration"]["param_one"] == "hello"
        assert tools[0]["configuration"]["param_two"] == 42
        assert tools[1]["configuration"]["threshold"] == 0.8
        assert tools[1]["configuration"]["label"] == "my_label"
    finally:
        ToolFactory.tool_config_map.pop("hetero_tool_a", None)
        ToolFactory.tool_config_map.pop("hetero_tool_b", None)


@pytest.mark.ai
def test_tool_build_config__exclude_defaults__omits_default_top_level_fields() -> None:
    """
    Purpose: Verify exclude_defaults=True omits fields equal to their declared default.
    Why this matters: Reduces payload size; only non-default values should be transmitted.
    Setup summary: Set some fields to non-default, leave others at default, assert correctly included/excluded.
    """
    ToolFactory.tool_config_map["excl_defaults_tool"] = SimpleToolConfig
    try:
        config = ToolBuildConfig(
            name="excl_defaults_tool",
            configuration=SimpleToolConfig(param_one="test", param_two=200),
            display_name="My Tool",
            selection_policy=ToolSelectionPolicy.ON_BY_DEFAULT,
        )

        result = config.model_dump(exclude_defaults=True)

        # Non-defaults must be present
        assert result.get("display_name") == "My Tool"
        assert result.get("selection_policy") == ToolSelectionPolicy.ON_BY_DEFAULT
        # Defaults must be absent: is_exclusive=False, is_sub_agent=False, is_enabled=True
        assert "is_exclusive" not in result
        assert "is_sub_agent" not in result
        assert "is_enabled" not in result
    finally:
        ToolFactory.tool_config_map.pop("excl_defaults_tool", None)


@pytest.mark.ai
def test_tool_build_config__exclude_defaults__propagates_into_configuration() -> None:
    """
    Purpose: Verify exclude_defaults=True drops default-valued fields inside the nested configuration.
    Why this matters: SerializeAsAny must forward dump kwargs into the subclass serialization.
    Setup summary: Config with mix of default/non-default subclass fields; assert correct exclusion.
    """
    ToolFactory.tool_config_map["excl_defaults_nested_tool"] = SimpleToolConfig
    try:
        # param_one default is "default", param_two default is 100
        config = ToolBuildConfig(
            name="excl_defaults_nested_tool",
            configuration=SimpleToolConfig(param_one="custom", param_two=100),
        )

        result = config.model_dump(exclude_defaults=True)
        cfg = result["configuration"]

        assert cfg.get("param_one") == "custom"  # non-default
        assert "param_two" not in cfg  # equals default 100
    finally:
        ToolFactory.tool_config_map.pop("excl_defaults_nested_tool", None)


@pytest.mark.ai
def test_tool_build_config__exclude_none__drops_none_fields_in_configuration() -> None:
    """
    Purpose: Verify exclude_none=True removes None-valued fields from the nested configuration.
    Why this matters: Prevents null noise in serialized payloads sent to downstream services.
    Setup summary: Config with optional None field; dump with exclude_none, assert field absent.
    """
    ToolFactory.tool_config_map["excl_none_tool"] = _NullableConfig
    try:
        config = ToolBuildConfig(
            name="excl_none_tool",
            configuration=_NullableConfig(value="present", optional_note=None),
        )

        result = config.model_dump(exclude_none=True)
        cfg = result["configuration"]

        assert cfg.get("value") == "present"
        assert "optional_note" not in cfg
    finally:
        ToolFactory.tool_config_map.pop("excl_none_tool", None)


@pytest.mark.ai
def test_tool_build_config__by_alias_and_exclude_defaults__combined() -> None:
    """
    Purpose: Verify by_alias=True and exclude_defaults=True work correctly together.
    Why this matters: Real API serialization uses both flags simultaneously.
    Setup summary: Non-default fields should appear camelCased; default fields should be absent.
    """
    ToolFactory.tool_config_map["combined_tool"] = _AnotherConfig
    try:
        config = ToolBuildConfig(
            name="combined_tool",
            configuration=_AnotherConfig(threshold=0.99, label="custom_label"),
            display_name="Combined",
            is_exclusive=True,
        )

        result = config.model_dump(by_alias=True, exclude_defaults=True)

        # Non-default top-level fields — camelCased
        assert result.get("displayName") == "Combined"
        assert result.get("isExclusive") is True
        # Default top-level fields — absent
        assert "isEnabled" not in result
        assert "isSubAgent" not in result
        # Non-default config fields — camelCased
        cfg = result["configuration"]
        assert cfg.get("threshold") == 0.99
        assert cfg.get("label") == "custom_label"
        # Default config field — absent (optional_note=None is the default)
        assert "optionalNote" not in cfg
    finally:
        ToolFactory.tool_config_map.pop("combined_tool", None)


# ============================================================================
# Graceful Degradation Tests (UN-17197)
# ============================================================================


@pytest.mark.ai
def test_tool_build_config__disables_tool__with_wrong_config_type(
    test_tool_class,
    test_tool_config_class,
) -> None:
    """
    Purpose: Verify tool with wrong config type is disabled instead of crashing.
    Why this matters: Graceful degradation when config type doesn't match tool.
    Setup summary: Register tool, provide wrong config type, assert tool is disabled.
    """
    # Arrange
    ToolFactory.register_tool(test_tool_class, test_tool_config_class)

    class WrongConfig(BaseToolConfig):
        wrong_param: str = "wrong"

    wrong_config = WrongConfig()
    config_data = {"name": "test_tool", "configuration": wrong_config}

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.is_enabled is False
    assert isinstance(config.configuration, BaseToolConfig)

    # Cleanup
    ToolFactory.tool_map.pop("test_tool", None)
    ToolFactory.tool_config_map.pop("test_tool", None)


@pytest.mark.ai
def test_tool_build_config__resolves_config__when_disabled_but_valid(
    register_simple_tool,
) -> None:
    """
    Purpose: Verify a disabled tool with a valid config keeps its concrete config type.
    Why this matters: Downstream validators key off the tool name and expect the
    concrete config (e.g. to read language_model_max_input_tokens). A disabled tool
    with a valid config must retain its resolved config, not a bare BaseToolConfig.
    Setup summary: Create a disabled config for a registered tool; assert config resolved.
    """
    # Arrange — "test_tool" is registered to SimpleToolConfig by the fixture
    config_data = {
        "name": "test_tool",
        "is_enabled": False,
        "configuration": {"param_one": "kept", "param_two": 321},
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert — stays disabled, but the concrete config is preserved
    assert config.is_enabled is False
    assert isinstance(config.configuration, SimpleToolConfig)
    assert config.configuration.param_one == "kept"
    assert config.configuration.param_two == 321


@pytest.mark.ai
def test_tool_build_config__demotes_disabled_tool__with_invalid_config() -> None:
    """
    Purpose: Verify a disabled tool with an invalid config is demoted, not crashed.
    Why this matters: Disabled tools may carry stale/garbage config; loading must not fail.
    Setup summary: Create config with is_enabled=False and unregistered name; assert fallback.
    """
    # Arrange — tool name is not registered, config is garbage, but tool is disabled
    config_data = {
        "name": "nonexistent_tool_xyz",
        "is_enabled": False,
        "configuration": {"completely": "invalid", "garbage": 999},
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.is_enabled is False
    assert config.name == "nonexistent_tool_xyz"
    assert isinstance(config.configuration, BaseToolConfig)


@pytest.mark.ai
def test_tool_build_config__demotes_disabled_tool__with_camel_case_key() -> None:
    """
    Purpose: Verify a disabled tool with an invalid config is demoted when isEnabled is camelCase.
    Why this matters: Backend payloads use alias_generator=to_camel keys.
    Setup summary: Create config with isEnabled=False and invalid config; assert fallback.
    """
    config_data = {
        "name": "nonexistent_tool_xyz",
        "isEnabled": False,
        "configuration": {"completely": "invalid", "garbage": 999},
    }

    config = ToolBuildConfig(**config_data)

    assert config.is_enabled is False
    assert config.name == "nonexistent_tool_xyz"
    assert isinstance(config.configuration, BaseToolConfig)


@pytest.mark.ai
def test_tool_build_config__demotes_disabled_tool__with_null_configuration() -> None:
    """
    Purpose: Verify a disabled tool with null configuration does not crash validation.
    Why this matters: Disabled tools may carry incomplete backend payloads.
    Setup summary: Create disabled config with configuration=null; assert BaseToolConfig fallback.
    """
    config_data = {
        "name": "disabled_tool",
        "isEnabled": False,
        "configuration": None,
    }

    config = ToolBuildConfig(**config_data)

    assert config.is_enabled is False
    assert isinstance(config.configuration, BaseToolConfig)


@pytest.mark.ai
def test_tool_build_config__disables_tool__when_demotion_overrides_camel_case_enabled(
    caplog,
) -> None:
    """
    Purpose: Verify demotion sets both is_enabled and isEnabled to false.
    Why this matters: Pydantic prefers alias keys when both snake and camel are present.
    Setup summary: Pass isEnabled=true with invalid config; assert tool ends disabled.
    """
    import logging

    config_data = {
        "name": "totally_unknown_tool",
        "isEnabled": True,
        "configuration": {"some_param": "value"},
    }

    with caplog.at_level(logging.WARNING):
        config = ToolBuildConfig(**config_data)

    assert config.is_enabled is False
    assert isinstance(config.configuration, BaseToolConfig)


@pytest.mark.ai
def test_tool_build_config__handles_mcp_tool__with_camel_case_mcp_source_id() -> None:
    """
    Purpose: Verify validator recognizes MCP tools when mcpSourceId uses camelCase.
    Why this matters: Backend payloads use camelCase alias keys for MCP metadata.
    Setup summary: Create config with mcpSourceId and assert factory validation is skipped.
    """
    config_data = {
        "name": "mcp_test_tool",
        "mcpSourceId": "mcp-server-123",
        "configuration": {
            "server_id": "server-123",
            "server_name": "Test Server",
            "mcpSourceId": "mcp-server-123",
        },
    }

    config = ToolBuildConfig(**config_data)

    assert config.name == "mcp_test_tool"
    assert isinstance(config.configuration, BaseToolConfig)


@pytest.mark.ai
def test_tool_build_config__disables_tool__with_unregistered_name(
    caplog,
) -> None:
    """
    Purpose: Verify unregistered tool name disables tool instead of crashing.
    Why this matters: Graceful degradation for unknown tools.
    Setup summary: Create config with unregistered tool name, assert is_enabled=False and warning logged.
    """
    import logging

    config_data = {
        "name": "totally_unknown_tool",
        "configuration": {"some_param": "value"},
    }

    # Act
    with caplog.at_level(logging.WARNING):
        config = ToolBuildConfig(**config_data)

    # Assert
    assert config.is_enabled is False
    assert isinstance(config.configuration, BaseToolConfig)
    assert "totally_unknown_tool" in caplog.text
    assert (
        "invalid configuration" in caplog.text.lower()
        or "disabled" in caplog.text.lower()
    )


@pytest.mark.ai
def test_tool_build_config__disables_tool__with_invalid_config_values(
    register_simple_tool,
    caplog,
) -> None:
    """
    Purpose: Verify registered tool with bad config values is disabled instead of crashing.
    Why this matters: Pydantic validation errors in config should not crash the system.
    Setup summary: Register tool, pass invalid config values, assert is_enabled=False.
    """
    import logging

    # SimpleToolConfig expects param_two: int, we pass a non-coercible string
    config_data = {
        "name": "test_tool",
        "configuration": {"param_one": "ok", "param_two": "not_an_integer_at_all"},
    }

    # Act
    with caplog.at_level(logging.WARNING):
        config = ToolBuildConfig(**config_data)

    # Assert
    assert config.is_enabled is False
    assert isinstance(config.configuration, BaseToolConfig)
    assert "test_tool" in caplog.text
