"""
Tests for unique_toolkit.agentic.tools.config module.

This module tests the configuration components for tools including:
- ToolIcon enum
- ToolSelectionPolicy enum
- handle_undefined_icon validator function
- ToolBuildConfig model with validation and serialization

Note on is_sub_agent:
    is_sub_agent is a computed property (not a stored field) derived from
    name == "SubAgentTool". It is True only for the SubAgentTool. When passing
    a dict with is_sub_agent=True or isSubAgent=True, the model validator
    sets name="SubAgentTool" and builds ExtendedSubAgentToolConfig. The
    computed property is included in model_dump/model_dump_json for API compatibility.
"""

import json
from typing import Any

import pytest

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

    Note: is_sub_agent is computed from name == "SubAgentTool". For name="test_tool"
    it evaluates to False.
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
    assert config.is_sub_agent is False  # Computed: name != "SubAgentTool"
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

    Note: is_sub_agent is a computed property, not a stored field. For
    name="full_test_tool" it evaluates to False (only True when name=="SubAgentTool").
    """
    # Arrange & Act
    config = ToolBuildConfig(
        name="full_test_tool",
        configuration=simple_config,
        display_name="Full Test Tool",
        icon=ToolIcon.ANALYTICS,
        selection_policy=ToolSelectionPolicy.FORCED_BY_DEFAULT,
        is_exclusive=True,
        is_enabled=False,
    )

    # Assert
    assert config.name == "full_test_tool"
    assert config.configuration == simple_config
    assert config.display_name == "Full Test Tool"
    assert config.icon == ToolIcon.ANALYTICS
    assert config.selection_policy == ToolSelectionPolicy.FORCED_BY_DEFAULT
    assert config.is_exclusive is True
    assert config.is_sub_agent is False  # Computed: name != "SubAgentTool"
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

    Flow: The validator reads is_sub_agent from the input dict, sets name="SubAgentTool",
    and builds ExtendedSubAgentToolConfig. The computed property is_sub_agent
    then returns True because name == "SubAgentTool".
    """
    # Arrange
    config_data = {
        "name": "sub_agent_test_tool",
        "is_sub_agent": True,  # Triggers validator to set name="SubAgentTool"
        "configuration": {
            "agent_name": "test_agent",
            "agent_description": "Test sub-agent",
            "system_prompt": "You are a test agent",
        },
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.name == "SubAgentTool"
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

    Same flow as is_sub_agent: validator checks value.get("isSubAgent") and
    sets name="SubAgentTool", so the computed is_sub_agent property returns True.
    """
    # Arrange
    config_data = {
        "name": "sub_agent_camel_test_tool",
        "isSubAgent": True,  # CamelCase variant; validator accepts both
        "configuration": {
            "agent_name": "test_agent",
            "agent_description": "Test sub-agent",
            "system_prompt": "You are a test agent",
        },
    }

    # Act
    config = ToolBuildConfig(**config_data)

    # Assert
    assert config.name == "SubAgentTool"
    assert config.is_sub_agent is True
    from unique_toolkit.agentic.tools.a2a import ExtendedSubAgentToolConfig

    assert isinstance(config.configuration, ExtendedSubAgentToolConfig)


@pytest.mark.ai
def test_tool_build_config__validates_config_type__with_wrong_type(
    test_tool_class,
    test_tool_config_class,
) -> None:
    """
    Purpose: Verify validator raises error when config type doesn't match tool.
    Why this matters: Ensures type safety between tool and configuration.
    Setup summary: Register tool, provide wrong config type, assert error raised.
    """
    # Arrange
    ToolFactory.register_tool(test_tool_class, test_tool_config_class)

    class WrongConfig(BaseToolConfig):
        wrong_param: str = "wrong"

    wrong_config = WrongConfig()
    config_data = {"name": "test_tool", "configuration": wrong_config}

    # Act & Assert
    # Pydantic v2 raises ValidationError for assertion failures
    from pydantic import ValidationError

    with pytest.raises((AssertionError, ValidationError)):
        ToolBuildConfig(**config_data)

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

    Note: Pydantic includes computed fields (e.g. is_sub_agent) in model_dump
    output, so APIs receiving the serialized config still see is_sub_agent.
    """
    # Arrange
    config = ToolBuildConfig(
        name="serialize_test",
        configuration=simple_config,
        display_name="Serialize Test",
        icon=ToolIcon.WORLD,
        selection_policy=ToolSelectionPolicy.ON_BY_DEFAULT,
        is_exclusive=True,
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
    assert result["is_sub_agent"] is False  # Computed field included in serialization
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

    Note: is_sub_agent is a computed field but is included in JSON output for
    API consumers; value is False when name != "SubAgentTool".
    """
    # Arrange
    config = ToolBuildConfig(
        name="json_test",
        configuration=simple_config,
        display_name="JSON Test",
        icon=ToolIcon.QUICK_REPLY,
        selection_policy=ToolSelectionPolicy.FORCED_BY_DEFAULT,
        is_exclusive=False,
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
    assert parsed["is_sub_agent"] is False  # Computed from name
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

    Note: is_sub_agent round-trips correctly because it is derived from name.
    When parsing, name is preserved; when name != "SubAgentTool", is_sub_agent
    is False. The parsed dict may include is_sub_agent from the JSON; it is
    ignored at init, and the computed value matches the original.
    """
    # Arrange
    original_config = ToolBuildConfig(
        name="round_trip_test",
        configuration=simple_config,
        display_name="Round Trip",
        icon=ToolIcon.CHAT_PLUS,
        selection_policy=ToolSelectionPolicy.ON_BY_DEFAULT,
        is_exclusive=True,
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
    assert (
        restored_config.is_sub_agent == original_config.is_sub_agent
    )  # Both computed from name
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
