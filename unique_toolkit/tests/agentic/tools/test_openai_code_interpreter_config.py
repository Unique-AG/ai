"""Tests for OpenAI code interpreter config (CodeInterpreterExtendedConfig and registration)."""

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterExtendedConfig,
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessorConfig,
)


@pytest.mark.ai
def test_code_interpreter_extended_config__has_defaults__when_constructed_with_no_args() -> (
    None
):
    """
    Purpose: Verify CodeInterpreterExtendedConfig provides sensible defaults for all nested configs.
    Why this matters: Ensures the extended config works out of the box without required args.
    Setup summary: Instantiate with no args; assert nested configs and tool_config exist.
    """
    # Act
    config = CodeInterpreterExtendedConfig()

    # Assert
    assert isinstance(
        config.generated_files_config, DisplayCodeInterpreterFilesPostProcessorConfig
    )
    assert config.generated_files_config.upload_to_chat is True
    assert config.generated_files_config.max_concurrent_file_downloads == 10
    assert isinstance(
        config.executed_code_display_config,
        ShowExecutedCodePostprocessorConfig,
    )
    assert config.executed_code_display_config.remove_from_history is True
    assert config.executed_code_display_config.sleep_time_before_display == 0.2
    assert isinstance(config.tool_config, OpenAICodeInterpreterConfig)
    assert config.tool_config.upload_files_in_chat_to_container is True


@pytest.mark.ai
def test_code_interpreter_extended_config__accepts_none_executed_code_display__for_deactivated() -> (
    None
):
    """
    Purpose: Verify executed_code_display_config can be None to deactivate code display.
    Why this matters: Allows disabling executed code prepending without changing other behavior.
    Setup summary: Construct with executed_code_display_config=None; assert it is None.
    """
    # Act
    config = CodeInterpreterExtendedConfig(executed_code_display_config=None)

    # Assert
    assert config.executed_code_display_config is None
