"""Tests for space diff normalization and helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from uqadm.space.diff import _normalize_for_diff, cmd_diff


def test_normalize_strips_ephemeral_keys_recursively() -> None:
    payload = {
        "id": "space_1",
        "moduleId": "mod_x",
        "createdAt": "t1",
        "companyId": "c1",
        "nested": {"createdAt": "x", "name": "n", "id": "inner"},
        "items": [{"updatedAt": "u", "moduleId": "m", "v": 1}],
        "keep": True,
    }
    out = _normalize_for_diff(payload, strict=False)
    assert out["keep"] is True
    assert "id" not in out
    assert "moduleId" not in out
    assert "createdAt" not in out
    assert "companyId" not in out
    assert "createdAt" not in out["nested"]
    assert "id" not in out["nested"]
    assert out["nested"]["name"] == "n"
    assert "updatedAt" not in out["items"][0]
    assert "moduleId" not in out["items"][0]
    assert out["items"][0]["v"] == 1


def test_normalize_strict_preserves_ephemeral_keys() -> None:
    payload = {"id": "x", "createdAt": "t"}
    assert _normalize_for_diff(payload, strict=True) == payload


def test_non_strict_normalize_strips_id() -> None:
    assert _normalize_for_diff({"id": 1, "a": 2}, strict=False) == {"a": 2}


def test_normalize_non_container() -> None:
    assert _normalize_for_diff("x", strict=False) == "x"
    assert _normalize_for_diff(None, strict=False) is None


# --- cmd_diff integration (with mocks) ---


@patch("uqadm.space.diff.Space.get_space")
@patch("uqadm.core.cli_auth.config_for_slot")
def test_cmd_diff_no_differences(
    mock_cfg: MagicMock,
    mock_get: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u", company_id="c")
    mock_get.return_value = {"id": "space_1", "name": "same"}
    cmd_diff(
        "a:space_1",
        "b:space_1",
        strict=False,
        output_format="unified",
        cwd=None,
    )
    out = capsys.readouterr().out
    assert "No differences." in out
    assert mock_get.call_count == 2


@patch("uqadm.space.diff.echo_credential_debug_if_auth_failure")
@patch("uqadm.space.diff.Space.get_space", side_effect=RuntimeError("boom"))
@patch("uqadm.core.cli_auth.config_for_slot")
def test_cmd_diff_source_fetch_error_exits_1(
    mock_cfg: MagicMock,
    mock_get: MagicMock,
    mock_debug: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u", company_id="c")
    with pytest.raises(SystemExit) as exc_info:
        cmd_diff(
            "a:space_1",
            "b:space_2",
            strict=False,
            output_format="unified",
            cwd=None,
        )
    assert exc_info.value.code == 1
    assert "diff failed fetching --source" in capsys.readouterr().err
    mock_debug.assert_called_once()


@patch("uqadm.space.diff.echo_credential_debug_if_auth_failure")
@patch("uqadm.space.diff.Space.get_space")
@patch("uqadm.core.cli_auth.config_for_slot")
def test_cmd_diff_destination_fetch_error_exits_1(
    mock_cfg: MagicMock,
    mock_get: MagicMock,
    mock_debug: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u", company_id="c")
    mock_get.side_effect = [{"id": "space_1"}, RuntimeError("boom")]
    with pytest.raises(SystemExit) as exc_info:
        cmd_diff(
            "a:space_1",
            "b:space_2",
            strict=False,
            output_format="unified",
            cwd=None,
        )
    assert exc_info.value.code == 1
    assert "diff failed fetching --destination" in capsys.readouterr().err
    mock_debug.assert_called_once()
