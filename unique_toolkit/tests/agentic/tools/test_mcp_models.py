"""
Test suite for MCP models.

This test suite validates the MCP data models:
1. MCPToolConfig structure and validation
2. MCPTool protocol definition (validated through usage)
"""

import pytest

from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig


class TestMCPToolConfig:
    """Test suite for MCPToolConfig model."""

    @pytest.mark.ai
    def test_create_config__with_all_required_fields__AI(self) -> None:
        """
        Purpose: Verify MCPToolConfig can be created with all required fields.
        Why this matters: Ensures the model structure is correct.
        Setup summary: Create config with all fields, verify values.
        """
        # Act
        config = MCPToolConfig(
            server_id="server_123",
            server_name="Test Server",
            server_system_prompt="System prompt",
            server_user_prompt="User prompt",
            mcp_source_id="source_456",
        )

        # Assert
        assert config.server_id == "server_123"
        assert config.server_name == "Test Server"
        assert config.server_system_prompt == "System prompt"
        assert config.server_user_prompt == "User prompt"
        assert config.mcp_source_id == "source_456"

    @pytest.mark.ai
    def test_create_config__with_optional_fields_as_none__AI(self) -> None:
        """
        Purpose: Verify MCPToolConfig handles optional fields being None.
        Why this matters: Not all servers provide system/user prompts.
        Setup summary: Create config with None optional fields, verify it works.
        """
        # Act
        config = MCPToolConfig(
            server_id="server_123",
            server_name="Test Server",
            server_system_prompt=None,
            server_user_prompt=None,
            mcp_source_id="source_456",
        )

        # Assert
        assert config.server_system_prompt is None
        assert config.server_user_prompt is None

    @pytest.mark.ai
    def test_config_is_base_tool_config__inherits_correctly__AI(self) -> None:
        """
        Purpose: Verify MCPToolConfig is a proper BaseToolConfig subclass.
        Why this matters: Ensures compatibility with tool factory system.
        Setup summary: Create config, verify it's a BaseToolConfig instance.
        """
        # Arrange
        from unique_toolkit.agentic.tools.schemas import BaseToolConfig

        # Act
        config = MCPToolConfig(
            server_id="server_123",
            server_name="Test Server",
            mcp_source_id="source_456",
        )

        # Assert
        assert isinstance(config, BaseToolConfig)

    @pytest.mark.ai
    def test_create_config__without_required_fields__raises_error__AI(self) -> None:
        """
        Purpose: Verify MCPToolConfig requires all mandatory fields.
        Why this matters: Ensures data integrity at model level.
        Setup summary: Try to create config without required fields, verify error.
        """
        # Act & Assert
        with pytest.raises(Exception):  # Pydantic validation error
            MCPToolConfig()

    @pytest.mark.ai
    def test_config_fields__are_accessible__as_attributes__AI(self) -> None:
        """
        Purpose: Verify all config fields are accessible as attributes.
        Why this matters: Enables easy access to configuration values.
        Setup summary: Create config, access all fields, verify values.
        """
        # Act
        config = MCPToolConfig(
            server_id="srv_001",
            server_name="Production Server",
            server_system_prompt="You are a helpful assistant",
            server_user_prompt="Please use this tool",
            mcp_source_id="mcp_source_789",
        )

        # Assert
        assert config.server_id == "srv_001"
        assert config.server_name == "Production Server"
        assert config.server_system_prompt == "You are a helpful assistant"
        assert config.server_user_prompt == "Please use this tool"
        assert config.mcp_source_id == "mcp_source_789"

    @pytest.mark.ai
    def test_config__can_be_serialized__to_dict__AI(self) -> None:
        """
        Purpose: Verify MCPToolConfig can be serialized to dictionary.
        Why this matters: Enables storage and transmission of config data.
        Setup summary: Create config, convert to dict, verify structure.
        """
        # Arrange
        config = MCPToolConfig(
            server_id="server_123",
            server_name="Test Server",
            server_system_prompt="System prompt",
            server_user_prompt="User prompt",
            mcp_source_id="source_456",
        )

        # Act
        config_dict = config.model_dump()

        # Assert
        assert isinstance(config_dict, dict)
        assert config_dict["server_id"] == "server_123"
        assert config_dict["server_name"] == "Test Server"
        assert config_dict["mcp_source_id"] == "source_456"

    @pytest.mark.ai
    def test_config__can_be_created_from_dict__AI(self) -> None:
        """
        Purpose: Verify MCPToolConfig can be created from dictionary.
        Why this matters: Enables loading config from stored data.
        Setup summary: Create dict, instantiate config from it, verify values.
        """
        # Arrange
        config_dict = {
            "server_id": "server_999",
            "server_name": "Dict Server",
            "server_system_prompt": "System",
            "server_user_prompt": "User",
            "mcp_source_id": "source_888",
        }

        # Act
        config = MCPToolConfig(**config_dict)

        # Assert
        assert config.server_id == "server_999"
        assert config.server_name == "Dict Server"
        assert config.mcp_source_id == "source_888"

    @pytest.mark.ai
    def test_config__handles_extra_whitespace__in_string_fields__AI(self) -> None:
        """
        Purpose: Verify MCPToolConfig handles string values with whitespace.
        Why this matters: Real-world data may have formatting issues.
        Setup summary: Create config with whitespace in fields, verify values preserved.
        """
        # Act
        config = MCPToolConfig(
            server_id="  server_123  ",
            server_name="  Test Server  ",
            server_system_prompt="  System prompt  ",
            server_user_prompt="  User prompt  ",
            mcp_source_id="  source_456  ",
        )

        # Assert - Values should be preserved as-is (no automatic trimming)
        assert config.server_id == "  server_123  "
        assert config.server_name == "  Test Server  "

    @pytest.mark.ai
    def test_config__with_empty_strings__in_optional_fields__AI(self) -> None:
        """
        Purpose: Verify MCPToolConfig handles empty strings in optional fields.
        Why this matters: Empty strings differ from None semantically.
        Setup summary: Create config with empty string prompts, verify they're preserved.
        """
        # Act
        config = MCPToolConfig(
            server_id="server_123",
            server_name="Test Server",
            server_system_prompt="",
            server_user_prompt="",
            mcp_source_id="source_456",
        )

        # Assert
        assert config.server_system_prompt == ""
        assert config.server_user_prompt == ""

    @pytest.mark.ai
    def test_config__multiple_instances__are_independent__AI(self) -> None:
        """
        Purpose: Verify multiple MCPToolConfig instances don't share state.
        Why this matters: Each tool needs independent configuration.
        Setup summary: Create two configs with different values, verify independence.
        """
        # Act
        config1 = MCPToolConfig(
            server_id="server_1",
            server_name="Server 1",
            mcp_source_id="source_1",
        )
        
        config2 = MCPToolConfig(
            server_id="server_2",
            server_name="Server 2",
            mcp_source_id="source_2",
        )

        # Assert
        assert config1.server_id != config2.server_id
        assert config1.server_name != config2.server_name
        assert config1.mcp_source_id != config2.mcp_source_id
        
        # Modifying one shouldn't affect the other
        config1.server_name = "Modified Server 1"
        assert config2.server_name == "Server 2"

