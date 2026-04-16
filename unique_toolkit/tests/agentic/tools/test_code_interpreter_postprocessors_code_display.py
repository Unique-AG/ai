"""Tests for code interpreter ShowExecutedCode postprocessor (config and behavior)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessor,
    ShowExecutedCodePostprocessorConfig,
)

CODE_DISPLAY_FF = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display.feature_flags"


@pytest.mark.ai
def test_show_executed_code_postprocessor_config__has_defaults__when_constructed_with_no_args() -> (
    None
):
    """
    Purpose: Verify ShowExecutedCodePostprocessorConfig defaults for remove_from_history, sleep_time, and enable.
    Why this matters: Ensures safe defaults for history, display timing, and enablement.
    Setup summary: Instantiate config with no args; assert default field values.
    """
    # Act
    config = ShowExecutedCodePostprocessorConfig()

    # Assert
    assert config.enable is True
    assert config.remove_from_history is True
    assert config.sleep_time_before_display == 0.2


@pytest.mark.ai
def test_show_executed_code_postprocessor__apply_postprocessing_to_response__prepends_code_block_to_message_text() -> (
    None
):
    """
    Purpose: Verify executed code is prepended to message text in details/code block format.
    Why this matters: Core behavior for displaying code interpreter output to the user.
    Setup summary: Build minimal loop_response with one code call and existing text; assert prepended format.
    """
    # Arrange
    config = ShowExecutedCodePostprocessorConfig()
    postprocessor = ShowExecutedCodePostprocessor(config=config)
    message = SimpleNamespace(text="Existing answer.")
    code_call = SimpleNamespace(code="print(1)")
    loop_response = SimpleNamespace(
        code_interpreter_calls=[code_call],
        message=message,
    )

    # Act
    changed = postprocessor.apply_postprocessing_to_response(loop_response)

    # Assert
    assert changed is True
    assert "Existing answer." in loop_response.message.text
    assert "print(1)" in loop_response.message.text
    assert "<details>" in loop_response.message.text
    assert "Code Interpreter Call" in loop_response.message.text
    assert "```python" in loop_response.message.text


@pytest.mark.ai
def test_show_executed_code_postprocessor__apply_postprocessing_to_response__returns_false_when_no_calls() -> (
    None
):
    """
    Purpose: Verify no change when there are no code interpreter calls.
    Why this matters: Avoids mutating message when nothing to display.
    Setup summary: loop_response with empty code_interpreter_calls; assert return False and text unchanged.
    """
    # Arrange
    config = ShowExecutedCodePostprocessorConfig()
    postprocessor = ShowExecutedCodePostprocessor(config=config)
    message = SimpleNamespace(text="Only text.")
    loop_response = SimpleNamespace(code_interpreter_calls=[], message=message)

    # Act
    changed = postprocessor.apply_postprocessing_to_response(loop_response)

    # Assert
    assert changed is False
    assert loop_response.message.text == "Only text."


@pytest.mark.ai
@pytest.mark.asyncio
async def test_show_executed_code_postprocessor__remove_from_text__strips_details_block__when_remove_from_history_true() -> (
    None
):
    """
    Purpose: Verify code interpreter details block is removed from text when remove_from_history is True.
    Why this matters: Keeps history clean when code blocks should not persist.
    Setup summary: Config with remove_from_history=True, text containing details block; assert block removed.
    """
    # Arrange
    config = ShowExecutedCodePostprocessorConfig(remove_from_history=True)
    postprocessor = ShowExecutedCodePostprocessor(config=config)
    text = (
        "<details><summary>Code Interpreter Call</summary>\n\n```python\nx = 1\n```\n\n</details>\n\n"
        "Here is the answer."
    )

    # Act
    result = await postprocessor.remove_from_text(text)

    # Assert
    assert "Code Interpreter Call" not in result
    assert "Here is the answer." in result
    assert "<details>" not in result


@pytest.mark.ai
@pytest.mark.asyncio
async def test_show_executed_code_postprocessor__remove_from_text__leaves_text_unchanged__when_remove_from_history_false() -> (
    None
):
    """
    Purpose: Verify text is returned unchanged when remove_from_history is False.
    Why this matters: Allows keeping executed code in history when desired.
    Setup summary: Config with remove_from_history=False; assert same string returned.
    """
    # Arrange
    config = ShowExecutedCodePostprocessorConfig(remove_from_history=False)
    postprocessor = ShowExecutedCodePostprocessor(config=config)
    text = "<details><summary>Code Interpreter Call</summary></details>Keep this."

    # Act
    result = await postprocessor.remove_from_text(text)

    # Assert
    assert result == text


@pytest.mark.ai
def test_show_executed_code_postprocessor__apply_postprocessing_to_response__no_op__when_fence_ff_on() -> (
    None
):
    """
    Purpose: Verify postprocessor is a no-op when the code execution fence FF is on.
    Why this matters: When the fence FF is on, fences in generated_files carry the code —
    adding <details> blocks here would duplicate content and could leak into the message.
    Setup summary: Patch FF to return True before construction; assert changed=False and text unchanged.
    """
    # Arrange
    config = ShowExecutedCodePostprocessorConfig()
    mock_ff = MagicMock()
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = True

    with patch(CODE_DISPLAY_FF, mock_ff):
        postprocessor = ShowExecutedCodePostprocessor(
            config=config, company_id="company-123"
        )

    message = SimpleNamespace(text="Existing answer.")
    code_call = SimpleNamespace(code="print(1)")
    loop_response = SimpleNamespace(
        code_interpreter_calls=[code_call],
        message=message,
    )

    # Act
    changed = postprocessor.apply_postprocessing_to_response(loop_response)

    # Assert
    assert changed is False
    assert loop_response.message.text == "Existing answer."
    assert "<details>" not in loop_response.message.text


@pytest.mark.ai
@pytest.mark.asyncio
async def test_show_executed_code_postprocessor__run__no_op__when_fence_ff_on() -> None:
    """
    Purpose: Verify run() skips the display sleep when FF is on.
    Why this matters: Avoids unnecessary delay when the postprocessor is a no-op.
    Setup summary: Patch FF on before construction; assert sleep not called.
    """
    import asyncio

    config = ShowExecutedCodePostprocessorConfig()
    mock_ff = MagicMock()
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = True

    with patch(CODE_DISPLAY_FF, mock_ff):
        postprocessor = ShowExecutedCodePostprocessor(
            config=config, company_id="company-123"
        )

    loop_response = SimpleNamespace(code_interpreter_calls=[])

    with patch.object(asyncio, "sleep") as mock_sleep:
        await postprocessor.run(loop_response)

    mock_sleep.assert_not_called()


@pytest.mark.ai
def test_show_executed_code_postprocessor__apply_postprocessing_to_response__no_op__when_enable_false() -> (
    None
):
    """
    Purpose: Verify postprocessor is a no-op when enable config flag is False.
    Why this matters: Users should be able to disable code display via configuration.
    Setup summary: Config with enable=False; assert changed=False and text unchanged.
    """
    # Arrange
    config = ShowExecutedCodePostprocessorConfig(enable=False)
    postprocessor = ShowExecutedCodePostprocessor(config=config)
    message = SimpleNamespace(text="Existing answer.")
    code_call = SimpleNamespace(code="print(1)")
    loop_response = SimpleNamespace(
        code_interpreter_calls=[code_call],
        message=message,
    )

    # Act
    changed = postprocessor.apply_postprocessing_to_response(loop_response)

    # Assert
    assert changed is False
    assert loop_response.message.text == "Existing answer."


@pytest.mark.ai
@pytest.mark.asyncio
async def test_show_executed_code_postprocessor__run__no_op__when_enable_false() -> (
    None
):
    """
    Purpose: Verify run() skips the display sleep when enable is False.
    Why this matters: Avoids unnecessary delay when the postprocessor is disabled via config.
    Setup summary: Config with enable=False; assert sleep not called.
    """
    import asyncio

    config = ShowExecutedCodePostprocessorConfig(enable=False)
    postprocessor = ShowExecutedCodePostprocessor(config=config)
    loop_response = SimpleNamespace(code_interpreter_calls=[])

    with patch.object(asyncio, "sleep") as mock_sleep:
        await postprocessor.run(loop_response)

    mock_sleep.assert_not_called()


@pytest.mark.ai
def test_show_executed_code_postprocessor__disabled_when_enable_false_even_if_ff_off() -> (
    None
):
    """
    Purpose: Verify enable=False disables the postprocessor regardless of feature flag state.
    Why this matters: The config flag should take precedence — if enable is False, the FF state shouldn't matter.
    Setup summary: Config with enable=False, FF off; assert still disabled.
    """
    # Arrange
    config = ShowExecutedCodePostprocessorConfig(enable=False)
    mock_ff = MagicMock()
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = False

    with patch(CODE_DISPLAY_FF, mock_ff):
        postprocessor = ShowExecutedCodePostprocessor(
            config=config, company_id="company-123"
        )

    message = SimpleNamespace(text="Existing answer.")
    code_call = SimpleNamespace(code="print(1)")
    loop_response = SimpleNamespace(
        code_interpreter_calls=[code_call],
        message=message,
    )

    # Act
    changed = postprocessor.apply_postprocessing_to_response(loop_response)

    # Assert
    assert changed is False
    assert loop_response.message.text == "Existing answer."
