"""Tests for code interpreter ShowExecutedCode postprocessor (config and behavior)."""

from types import SimpleNamespace

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessor,
    ShowExecutedCodePostprocessorConfig,
)


@pytest.mark.ai
def test_show_executed_code_postprocessor_config__has_defaults__when_constructed_with_no_args() -> (
    None
):
    """
    Purpose: Verify ShowExecutedCodePostprocessorConfig defaults for remove_from_history.
    Why this matters: Ensures the legacy <details> block is stripped from history by default.
    Setup summary: Instantiate config with no args; assert default field values.
    """
    # Act
    config = ShowExecutedCodePostprocessorConfig()

    # Assert
    assert config.remove_from_history is True


@pytest.mark.ai
def test_show_executed_code_postprocessor__apply_postprocessing_to_response__never_prepends_code_block() -> (
    None
):
    """
    Purpose: Verify executed code is never prepended to the message text.
    Why this matters: Code interpreter output is always rendered as codeExecution fences
    (UN-25450); a <details> block here would duplicate the code inside those fences.
    Setup summary: Build a loop_response with one code call and existing text; assert
    changed=False and the text is untouched.
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
    assert changed is False
    assert loop_response.message.text == "Existing answer."
    assert "<details>" not in loop_response.message.text


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
async def test_show_executed_code_postprocessor__run__is_a_no_op() -> None:
    """
    Purpose: Verify run() does no work and returns None.
    Why this matters: Nothing has to be resolved before apply_postprocessing_to_response
    any more, so the turn should not pay for a sleep or a flag lookup here.
    Setup summary: Call run() with an empty loop_response; assert it returns None.
    """
    # Arrange
    config = ShowExecutedCodePostprocessorConfig()
    postprocessor = ShowExecutedCodePostprocessor(config=config)
    loop_response = SimpleNamespace(code_interpreter_calls=[])

    # Act
    result = await postprocessor.run(loop_response)

    # Assert
    assert result is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_show_executed_code_postprocessor__remove_from_text__strips_details_block__when_remove_from_history_true() -> (
    None
):
    """
    Purpose: Verify code interpreter details block is removed from text when remove_from_history is True.
    Why this matters: Messages written before UN-25450 still hold the old <details> block;
    it must not go back to the model as part of the history.
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
