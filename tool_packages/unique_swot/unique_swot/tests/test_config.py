"""Tests for the SwotAnalysisToolConfig."""


from unique_swot.config import SwotAnalysisToolConfig


def test_config_cache_scope_id_has_default():
    """Test that cache_scope_id has a default empty string value."""
    # Create config without specifying cache_scope_id
    config = SwotAnalysisToolConfig()

    # Verify the default value
    assert config.cache_scope_id == ""
    assert isinstance(config.cache_scope_id, str)


def test_config_cache_scope_id_can_be_set():
    """Test that cache_scope_id can be explicitly set."""
    # Create config with a specific cache_scope_id
    test_scope_id = "test-scope-123"
    config = SwotAnalysisToolConfig(cache_scope_id=test_scope_id)

    # Verify the value is set correctly
    assert config.cache_scope_id == test_scope_id


def test_config_has_required_nested_configs():
    """Test that the config includes all required nested configurations."""
    config = SwotAnalysisToolConfig()

    # Verify nested config attributes exist
    assert hasattr(config, "source_management_config")
    assert hasattr(config, "report_generation_config")
    assert hasattr(config, "report_summarization_config")
    assert hasattr(config, "report_renderer_config")
    assert hasattr(config, "language_model")


def test_config_tool_description_fields_exist():
    """Test that tool description fields are present in the config."""
    config = SwotAnalysisToolConfig()

    # Verify tool description fields
    assert hasattr(config, "tool_description")
    assert hasattr(config, "tool_description_for_system_prompt")
    assert hasattr(config, "tool_format_information_for_system_prompt")
    assert hasattr(config, "tool_description_for_user_prompt")
    assert hasattr(config, "tool_format_information_for_user_prompt")
    assert hasattr(config, "tool_format_reminder_for_user_prompt")

    # Verify they are strings
    assert isinstance(config.tool_description, str)
    assert isinstance(config.tool_description_for_system_prompt, str)
