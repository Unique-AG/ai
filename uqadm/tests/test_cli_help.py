"""Tests for CLI help output (Typer-based entry point)."""

from typing import Callable

from typer.testing import CliRunner

from uqadm.cli import app

# Plain help text: Rich markup + ANSI breaks substring assertions in CI narrow TTY.
_HelpInvoker = Callable[[list[str]], str]


def _make_help_invoker() -> _HelpInvoker:
    runner = CliRunner()

    def _invoke(args: list[str]) -> str:
        result = runner.invoke(app, args, color=False)
        assert result.exit_code == 0
        return result.output

    return _invoke


def test_space_export_help_shows_space_id_arg() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["space", "export", "--help"])
    assert "SPACE_ID" in result_output
    assert "--slot" in result_output


def test_space_upsert_help_shows_file_and_target_options() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["space", "upsert", "--help"])
    assert "--file" in result_output
    assert "--target" in result_output
    assert "--slot" in result_output


def test_space_delete_help_shows_space_id_arg() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["space", "delete", "--help"])
    assert "SPACE_ID" in result_output
    assert "--slot" in result_output


def test_space_diff_help_shows_source_and_destination() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["space", "diff", "--help"])
    assert "--source" in result_output
    assert "--destination" in result_output


def test_space_list_help_shows_slot_option() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["space", "list", "--help"])
    assert "--slot" in result_output


def test_top_level_help_shows_commands_and_globals() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["--help"])
    assert "space" in result_output
    assert "chat" in result_output
    assert "env" in result_output
    assert "install" in result_output
    assert "--cwd" in result_output
    assert "--version" in result_output


def test_top_level_cwd_option_is_documented() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["--help"])
    assert "--cwd" in result_output


def test_chat_send_help() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["chat", "send", "--help"])
    assert "ASSISTANT_ID" in result_output
    assert "--text" in result_output
    assert "--slot" in result_output
    assert "--chat-id" in result_output


def test_chat_history_help() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["chat", "history", "--help"])
    assert "CHAT_ID" in result_output
    assert "--max-tokens" in result_output
    assert "--slot" in result_output


def test_env_help_shows_subcommands() -> None:
    invoke_help = _make_help_invoker()
    result_output = invoke_help(["env", "--help"])
    assert "create" in result_output
    assert "list" in result_output
    assert "show" in result_output
    assert "set-default" in result_output
    assert "delete" in result_output


def test_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "uqadm" in result.output
