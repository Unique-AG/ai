"""Tests for ``uqadm space_delete`` command helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from uqadm.space_delete import cmd_delete


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
