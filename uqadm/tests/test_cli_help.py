"""Tests for nested ``--help`` documenting inherited ``uqadm`` flags."""

from click.testing import CliRunner

from uqadm.cli import main


def test_space_export_help_shows_source_option() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["space", "export", "--help"])
    assert result.exit_code == 0
    assert "--source" in result.output


def test_space_upsert_help_shows_destination_and_file_options() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["space", "upsert", "--help"])
    assert result.exit_code == 0
    assert "--destination" in result.output
    assert "--file" in result.output


def test_space_delete_help_shows_source_option() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["space", "delete", "--help"])
    assert result.exit_code == 0
    assert "--source" in result.output


def test_space_diff_help_shows_source_and_destination() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["space", "diff", "--help"])
    assert result.exit_code == 0
    assert "--source" in result.output
    assert "--destination" in result.output


def test_space_list_help_shows_slot_option() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["space", "list", "--help"])
    assert result.exit_code == 0
    assert "--slot" in result.output


def test_space_help_includes_global_options() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["space", "--help"])
    assert result.exit_code == 0
    assert "Global options (uqadm)" in result.output
    assert "--cwd" in result.output
    assert "--version" in result.output
    assert "Examples:" in result.output
    assert "uqadm space export" in result.output


def test_space_list_help_includes_global_options() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["space", "list", "--help"])
    assert result.exit_code == 0
    assert "Global options (uqadm)" in result.output
    assert "--cwd" in result.output
    assert "Examples:" in result.output
    assert "uqadm space list --slot qa" in result.output


def test_top_level_help_shows_commands_and_globals() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Commands:" in result.output
    assert "space" in result.output
    assert "--cwd" in result.output
    assert "--version" in result.output
    assert "Examples:" in result.output
    assert "uqadm space list --slot qa" in result.output
