"""Tests for hosted shell config (HostedShellExtendedConfig and registration)."""

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.hosted_shell.config import (
    HostedShellExtendedConfig,
    InlineSkillConfig,
    OpenAIHostedShellConfig,
    SkillReferenceConfig,
)


@pytest.mark.ai
def test_hosted_shell_config__has_defaults__when_constructed_with_no_args() -> None:
    """
    Purpose: Verify OpenAIHostedShellConfig provides sensible defaults.
    Why this matters: Ensures the config works out of the box.
    Setup summary: Instantiate with no args; assert default field values.
    """
    # Act
    config = OpenAIHostedShellConfig()

    # Assert
    assert config.skill_references == []
    assert config.inline_skills == []
    assert config.upload_files_in_chat_to_container is True
    assert config.expires_after_minutes == 20
    assert config.use_auto_container is True


@pytest.mark.ai
def test_hosted_shell_extended_config__has_defaults__when_constructed_with_no_args() -> (
    None
):
    """
    Purpose: Verify HostedShellExtendedConfig provides sensible defaults for all nested configs.
    Why this matters: Ensures the extended config works out of the box without required args.
    Setup summary: Instantiate with no args; assert nested configs and tool_config exist.
    """
    # Act
    config = HostedShellExtendedConfig()

    # Assert
    assert isinstance(
        config.generated_files_config, DisplayCodeInterpreterFilesPostProcessorConfig
    )
    assert config.generated_files_config.upload_to_chat is True
    assert config.generated_files_config.max_concurrent_file_downloads == 10
    assert isinstance(
        config.executed_command_display_config,
        ShowExecutedCodePostprocessorConfig,
    )
    assert config.executed_command_display_config.remove_from_history is True
    assert config.executed_command_display_config.sleep_time_before_display == 0.2
    assert isinstance(config.tool_config, OpenAIHostedShellConfig)
    assert config.tool_config.upload_files_in_chat_to_container is True
    assert config.tool_config.use_auto_container is True


@pytest.mark.ai
def test_hosted_shell_extended_config__defaults_executed_command_display__when_none_passed() -> (
    None
):
    """
    Purpose: Verify executed_command_display_config falls back to default when None is passed.
    Why this matters: The field validator converts None to the default config.
    Setup summary: Construct with executed_command_display_config=None; assert it gets the default.
    """
    # Act
    config = HostedShellExtendedConfig(executed_command_display_config=None)

    # Assert
    assert isinstance(
        config.executed_command_display_config, ShowExecutedCodePostprocessorConfig
    )
    assert config.executed_command_display_config.remove_from_history is True


@pytest.mark.ai
def test_skill_reference_config__stores_skill_id_and_version() -> None:
    """
    Purpose: Verify SkillReferenceConfig correctly stores skill_id and version.
    Why this matters: Skill references must pass correct identifiers to the API.
    Setup summary: Construct with explicit values; assert fields match.
    """
    # Act
    config = SkillReferenceConfig(skill_id="skill_abc123", version="2")

    # Assert
    assert config.skill_id == "skill_abc123"
    assert config.version == "2"


@pytest.mark.ai
def test_skill_reference_config__version_defaults_to_none() -> None:
    """
    Purpose: Verify SkillReferenceConfig version defaults to None.
    Why this matters: When version is None, the API uses the default version.
    Setup summary: Construct with only skill_id; assert version is None.
    """
    # Act
    config = SkillReferenceConfig(skill_id="skill_abc123")

    # Assert
    assert config.version is None


@pytest.mark.ai
def test_inline_skill_config__stores_all_fields() -> None:
    """
    Purpose: Verify InlineSkillConfig correctly stores name, description, and base64_zip.
    Why this matters: Inline skills must carry all metadata and payload.
    Setup summary: Construct with explicit values; assert fields match.
    """
    # Act
    config = InlineSkillConfig(
        name="data-analyzer",
        description="Analyzes CSV data",
        base64_zip="UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==",
    )

    # Assert
    assert config.name == "data-analyzer"
    assert config.description == "Analyzes CSV data"
    assert config.base64_zip == "UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA=="


@pytest.mark.ai
def test_hosted_shell_config__with_skill_references__stores_list() -> None:
    """
    Purpose: Verify skill_references list is stored correctly on the config.
    Why this matters: The tool must pass skill refs through to the API.
    Setup summary: Construct config with one skill reference; assert list contents.
    """
    # Arrange
    skill_ref = SkillReferenceConfig(skill_id="skill_123", version="latest")

    # Act
    config = OpenAIHostedShellConfig(skill_references=[skill_ref])

    # Assert
    assert len(config.skill_references) == 1
    assert config.skill_references[0].skill_id == "skill_123"
    assert config.skill_references[0].version == "latest"


@pytest.mark.ai
def test_hosted_shell_config__with_inline_skills__stores_list() -> None:
    """
    Purpose: Verify inline_skills list is stored correctly on the config.
    Why this matters: Inline skills must be passed to the API environment.
    Setup summary: Construct config with one inline skill; assert list contents.
    """
    # Arrange
    inline = InlineSkillConfig(
        name="test-skill",
        description="A test skill",
        base64_zip="dGVzdA==",
    )

    # Act
    config = OpenAIHostedShellConfig(inline_skills=[inline])

    # Assert
    assert len(config.inline_skills) == 1
    assert config.inline_skills[0].name == "test-skill"
