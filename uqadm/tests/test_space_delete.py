"""Tests for ``uqadm space_delete`` command helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from uqadm.space_delete import (
    _format_space_label,
    cmd_delete,
    sanitize_terminal_label,
)


def test_delete_invalid_spec_exits_2() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cmd_delete("slot_only_no_space_id", yes=False, dry_run=False, cwd=None)
    assert exc_info.value.code == 2


@patch("uqadm.space_delete.config_for_slot")
@patch("uqadm.space_delete.Space.delete_space")
@patch("uqadm.space_delete.Space.get_space")
def test_delete_dry_run_fetches_but_skips_delete(
    mock_get: MagicMock,
    mock_del: MagicMock,
    mock_cfg: MagicMock,
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u1", company_id="c1")
    mock_get.return_value = {"name": "My Space", "uiType": "DEFAULT"}
    cmd_delete("1:space_x", yes=False, dry_run=True, cwd=None)
    mock_get.assert_called_once_with("u1", "c1", "space_x")
    mock_del.assert_not_called()


@patch("uqadm.space_delete.click.confirm", return_value=False)
@patch("uqadm.space_delete.config_for_slot")
@patch("uqadm.space_delete.Space.delete_space")
@patch("uqadm.space_delete.Space.get_space")
def test_delete_prompt_abort_skips_delete(
    mock_get: MagicMock,
    mock_del: MagicMock,
    mock_cfg: MagicMock,
    _mock_confirm: MagicMock,
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u1", company_id="c1")
    mock_get.return_value = {"name": "N", "uiType": "DEFAULT"}
    cmd_delete("1:space_x", yes=False, dry_run=False, cwd=None)
    mock_del.assert_not_called()


@patch("uqadm.space_delete.click.confirm")
@patch("uqadm.space_delete.config_for_slot")
@patch("uqadm.space_delete.Space.delete_space")
@patch("uqadm.space_delete.Space.get_space")
def test_delete_yes_skips_confirm_and_calls_delete(
    mock_get: MagicMock,
    mock_del: MagicMock,
    mock_cfg: MagicMock,
    mock_confirm: MagicMock,
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u1", company_id="c1")
    mock_get.return_value = {"name": "N", "uiType": "DEFAULT"}
    cmd_delete("1:space_x", yes=True, dry_run=False, cwd=None)
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
    assert "'DEFAULT" in label  # uiType is now repr-quoted

    raw_label = _format_space_label({"name": "Demo", "uiType": "DEFAULT"})
    assert raw_label == "'Demo' (uiType='DEFAULT')"
