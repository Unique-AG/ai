"""Tests for ``uqadm space delete`` command helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from uqadm.space.delete import (
    _format_space_label,
    cmd_delete,
    sanitize_terminal_label,
)


def test_delete_invalid_space_id_exits_2() -> None:
    """A colon-only spec with no id after it should exit with code 2."""
    cfg = MagicMock(user_id="u1", company_id="c1")
    with pytest.raises(SystemExit) as exc_info:
        cmd_delete("slot:", cfg=cfg, yes=False, dry_run=False)
    assert exc_info.value.code == 2


@patch("uqadm.space.delete.Space.delete_space")
@patch("uqadm.space.delete.Space.get_space")
def test_delete_dry_run_fetches_but_skips_delete(
    mock_get: MagicMock,
    mock_del: MagicMock,
) -> None:
    cfg = MagicMock(user_id="u1", company_id="c1")
    mock_get.return_value = {"name": "My Space", "uiType": "DEFAULT"}
    cmd_delete("space_x", cfg=cfg, yes=False, dry_run=True)
    mock_get.assert_called_once_with("u1", "c1", "space_x")
    mock_del.assert_not_called()


@patch("uqadm.space.delete.typer.confirm", return_value=False)
@patch("uqadm.space.delete.Space.delete_space")
@patch("uqadm.space.delete.Space.get_space")
def test_delete_prompt_abort_skips_delete(
    mock_get: MagicMock,
    mock_del: MagicMock,
    _mock_confirm: MagicMock,
) -> None:
    cfg = MagicMock(user_id="u1", company_id="c1")
    mock_get.return_value = {"name": "N", "uiType": "DEFAULT"}
    cmd_delete("space_x", cfg=cfg, yes=False, dry_run=False)
    mock_del.assert_not_called()


@patch("uqadm.space.delete.typer.confirm")
@patch("uqadm.space.delete.Space.delete_space")
@patch("uqadm.space.delete.Space.get_space")
def test_delete_yes_skips_confirm_and_calls_delete(
    mock_get: MagicMock,
    mock_del: MagicMock,
    mock_confirm: MagicMock,
) -> None:
    cfg = MagicMock(user_id="u1", company_id="c1")
    mock_get.return_value = {"name": "N", "uiType": "DEFAULT"}
    cmd_delete("space_x", cfg=cfg, yes=True, dry_run=False)
    mock_confirm.assert_not_called()
    mock_del.assert_called_once_with("u1", "c1", "space_x")


def test_sanitize_terminal_label_preserves_plain_text() -> None:
    assert sanitize_terminal_label("Hello World") == "Hello World"


def test_sanitize_terminal_label_preserves_common_whitespace() -> None:
    assert sanitize_terminal_label("a\tb\nc\rd") == "a\tb\nc\rd"


def test_sanitize_terminal_label_strips_c0_escape() -> None:
    cleaned = sanitize_terminal_label("safe\x1b[31mDANGER\x1b[0m")
    assert "\x1b" not in cleaned
    assert "safe" in cleaned
    assert "DANGER" in cleaned


def test_sanitize_terminal_label_strips_c1_controls() -> None:
    cleaned = sanitize_terminal_label("a\x9bb\x80c")
    assert "\x9b" not in cleaned
    assert "\x80" not in cleaned
    assert cleaned.startswith("a")
    assert cleaned.endswith("c")


def test_sanitize_terminal_label_strips_del_character() -> None:
    cleaned = sanitize_terminal_label("a\x7fb")
    assert "\x7f" not in cleaned


def test_sanitize_terminal_label_coerces_non_string() -> None:
    assert sanitize_terminal_label(42) == "42"
    assert sanitize_terminal_label(None) == "None"


def test_format_space_label_quotes_ui_type_and_strips_escape() -> None:
    label = _format_space_label({"name": "Demo", "uiType": "DEFAULT\x1b[31mhack"})
    assert "\x1b" not in label
    assert "uiType=" in label
    assert "'DEFAULT" in label

    raw_label = _format_space_label({"name": "Demo", "uiType": "DEFAULT"})
    assert raw_label == "'Demo' (uiType='DEFAULT')"
