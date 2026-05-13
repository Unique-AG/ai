"""Tests for CLI help output (Typer-based entry point)."""

from typer.testing import CliRunner

from uqadm.cli import app


def test_space_export_help_shows_space_id_arg() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["space", "export", "--help"])
    assert result.exit_code == 0
    assert "SPACE_ID" in result.output
    assert "--slot" in result.output


def test_space_upsert_help_shows_file_and_target_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["space", "upsert", "--help"])
    assert result.exit_code == 0
    assert "--file" in result.output
    assert "--target" in result.output
    assert "--slot" in result.output


def test_space_delete_help_shows_space_id_arg() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["space", "delete", "--help"])
    assert result.exit_code == 0
    assert "SPACE_ID" in result.output
    assert "--slot" in result.output


def test_space_diff_help_shows_source_and_destination() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["space", "diff", "--help"])
    assert result.exit_code == 0
    assert "--source" in result.output
    assert "--destination" in result.output


def test_space_list_help_shows_slot_option() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["space", "list", "--help"])
    assert result.exit_code == 0
    assert "--slot" in result.output


def test_top_level_help_shows_commands_and_globals() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "space" in result.output
    assert "chat" in result.output
    assert "env" in result.output
    assert "install" in result.output
    assert "--cwd" in result.output
    assert "--version" in result.output


def test_top_level_cwd_option_is_documented() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--cwd" in result.output


def test_chat_send_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["chat", "send", "--help"])
    assert result.exit_code == 0
    assert "ASSISTANT_ID" in result.output
    assert "--text" in result.output
    assert "--slot" in result.output
    assert "--chat-id" in result.output


def test_chat_history_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["chat", "history", "--help"])
    assert result.exit_code == 0
    assert "CHAT_ID" in result.output
    assert "--max-tokens" in result.output
    assert "--slot" in result.output


def test_env_help_shows_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["env", "--help"])
    assert result.exit_code == 0
    assert "create" in result.output
    assert "list" in result.output
    assert "show" in result.output
    assert "set-default" in result.output
    assert "delete" in result.output


def test_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "uqadm" in result.output
