"""Tests for hosted shell ShowExecutedCommand postprocessor (config and behavior)."""

from types import SimpleNamespace

import pytest

from unique_toolkit.agentic.tools.openai_builtin.hosted_shell.postprocessors.command_display import (
    ShowExecutedCommandPostprocessor,
    ShowExecutedCommandPostprocessorConfig,
)


@pytest.mark.ai
def test_show_executed_command_postprocessor_config__has_defaults__when_constructed_with_no_args() -> (
    None
):
    """
    Purpose: Verify ShowExecutedCommandPostprocessorConfig defaults.
    Why this matters: Ensures safe defaults for history and display timing.
    Setup summary: Instantiate config with no args; assert default field values.
    """
    # Act
    config = ShowExecutedCommandPostprocessorConfig()

    # Assert
    assert config.remove_from_history is True
    assert config.sleep_time_before_display == 0.2


@pytest.mark.ai
def test_show_executed_command_postprocessor__apply_postprocessing_to_response__prepends_command_block_to_message_text() -> (
    None
):
    """
    Purpose: Verify executed shell commands are prepended to message text in details/code block format.
    Why this matters: Core behavior for displaying shell output to the user.
    Setup summary: Build minimal loop_response with one shell call and existing text; assert prepended format.
    """
    # Arrange
    config = ShowExecutedCommandPostprocessorConfig()
    postprocessor = ShowExecutedCommandPostprocessor(config=config)
    message = SimpleNamespace(text="Existing answer.")
    action = SimpleNamespace(commands=["ls -la /mnt/data", "python script.py"])
    shell_call = SimpleNamespace(action=action)
    loop_response = SimpleNamespace(
        shell_calls=[shell_call],
        message=message,
    )

    # Act
    changed = postprocessor.apply_postprocessing_to_response(loop_response)

    # Assert
    assert changed is True
    assert "Existing answer." in loop_response.message.text
    assert "ls -la /mnt/data" in loop_response.message.text
    assert "python script.py" in loop_response.message.text
    assert "<details>" in loop_response.message.text
    assert "Shell Command" in loop_response.message.text
    assert "```bash" in loop_response.message.text


@pytest.mark.ai
def test_show_executed_command_postprocessor__apply_postprocessing_to_response__returns_false_when_no_calls() -> (
    None
):
    """
    Purpose: Verify no change when there are no shell calls.
    Why this matters: Avoids mutating message when nothing to display.
    Setup summary: loop_response with empty shell_calls; assert return False and text unchanged.
    """
    # Arrange
    config = ShowExecutedCommandPostprocessorConfig()
    postprocessor = ShowExecutedCommandPostprocessor(config=config)
    message = SimpleNamespace(text="Only text.")
    loop_response = SimpleNamespace(shell_calls=[], message=message)

    # Act
    changed = postprocessor.apply_postprocessing_to_response(loop_response)

    # Assert
    assert changed is False
    assert loop_response.message.text == "Only text."


@pytest.mark.ai
def test_show_executed_command_postprocessor__apply_postprocessing_to_response__handles_multiple_calls() -> (
    None
):
    """
    Purpose: Verify multiple shell calls are all prepended.
    Why this matters: Users may see multiple commands executed in one response.
    Setup summary: Two shell calls with different commands; assert both appear in text.
    """
    # Arrange
    config = ShowExecutedCommandPostprocessorConfig()
    postprocessor = ShowExecutedCommandPostprocessor(config=config)
    message = SimpleNamespace(text="Done.")
    call_1 = SimpleNamespace(action=SimpleNamespace(commands=["echo hello"]))
    call_2 = SimpleNamespace(action=SimpleNamespace(commands=["cat data.csv"]))
    loop_response = SimpleNamespace(
        shell_calls=[call_1, call_2],
        message=message,
    )

    # Act
    changed = postprocessor.apply_postprocessing_to_response(loop_response)

    # Assert
    assert changed is True
    assert "echo hello" in loop_response.message.text
    assert "cat data.csv" in loop_response.message.text
    assert loop_response.message.text.count("<details>") == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_show_executed_command_postprocessor__remove_from_text__strips_details_block__when_remove_from_history_true() -> (
    None
):
    """
    Purpose: Verify shell command details block is removed from text when remove_from_history is True.
    Why this matters: Keeps history clean when command blocks should not persist.
    Setup summary: Config with remove_from_history=True, text containing details block; assert block removed.
    """
    # Arrange
    config = ShowExecutedCommandPostprocessorConfig(remove_from_history=True)
    postprocessor = ShowExecutedCommandPostprocessor(config=config)
    text = (
        "<details><summary>Shell Command</summary>\n\n```bash\nls -la\n```\n\n</details>\n\n"
        "Here is the answer."
    )

    # Act
    result = await postprocessor.remove_from_text(text)

    # Assert
    assert "Shell Command" not in result
    assert "Here is the answer." in result
    assert "<details>" not in result


@pytest.mark.ai
@pytest.mark.asyncio
async def test_show_executed_command_postprocessor__remove_from_text__leaves_text_unchanged__when_remove_from_history_false() -> (
    None
):
    """
    Purpose: Verify text is returned unchanged when remove_from_history is False.
    Why this matters: Allows keeping executed commands in history when desired.
    Setup summary: Config with remove_from_history=False; assert same string returned.
    """
    # Arrange
    config = ShowExecutedCommandPostprocessorConfig(remove_from_history=False)
    postprocessor = ShowExecutedCommandPostprocessor(config=config)
    text = "<details><summary>Shell Command</summary></details>Keep this."

    # Act
    result = await postprocessor.remove_from_text(text)

    # Assert
    assert result == text
