"""Tests for deprecated responses_api code interpreter postprocessor re-exports."""

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessor as NewShowExecutedCodePostprocessor,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessorConfig as NewShowExecutedCodePostprocessorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessor as NewDisplayCodeInterpreterFilesPostProcessor,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessorConfig as NewDisplayCodeInterpreterFilesPostProcessorConfig,
)


@pytest.mark.ai
def test_deprecated_code_display_reexports__subclass_new_implementations__when_imported_from_responses_api() -> (
    None
):
    """
    Purpose: Verify deprecated responses_api code_display exports are subclasses of the new openai_builtin classes.
    Why this matters: Backward compatibility for code still importing from the old path.
    Setup summary: Import from deprecated module; assert issubclass of new implementations.
    """
    from unique_toolkit.agentic.responses_api.postprocessors.code_display import (
        ShowExecutedCodePostprocessor,
        ShowExecutedCodePostprocessorConfig,
    )

    assert issubclass(ShowExecutedCodePostprocessor, NewShowExecutedCodePostprocessor)
    assert issubclass(
        ShowExecutedCodePostprocessorConfig, NewShowExecutedCodePostprocessorConfig
    )


@pytest.mark.ai
def test_deprecated_generated_files_reexports__subclass_new_implementations__when_imported_from_responses_api() -> (
    None
):
    """
    Purpose: Verify deprecated responses_api generated_files exports are subclasses of the new openai_builtin classes.
    Why this matters: Backward compatibility for code still importing from the old path.
    Setup summary: Import from deprecated module; assert issubclass of new implementations.
    """
    from unique_toolkit.agentic.responses_api.postprocessors.generated_files import (
        DisplayCodeInterpreterFilesPostProcessor,
        DisplayCodeInterpreterFilesPostProcessorConfig,
    )

    assert issubclass(
        DisplayCodeInterpreterFilesPostProcessor,
        NewDisplayCodeInterpreterFilesPostProcessor,
    )
    assert issubclass(
        DisplayCodeInterpreterFilesPostProcessorConfig,
        NewDisplayCodeInterpreterFilesPostProcessorConfig,
    )


@pytest.mark.ai
def test_deprecated_code_display_config__instantiable_with_same_defaults__as_new_config() -> (
    None
):
    """
    Purpose: Verify deprecated ShowExecutedCodePostprocessorConfig can be used like the new one.
    Why this matters: Callers can swap import path without code changes.
    Setup summary: Instantiate deprecated config with no args; assert same defaults as new.
    """
    from unique_toolkit.agentic.responses_api.postprocessors.code_display import (
        ShowExecutedCodePostprocessorConfig,
    )

    config = ShowExecutedCodePostprocessorConfig()
    assert config.remove_from_history is True
    assert config.sleep_time_before_display == 0.2
