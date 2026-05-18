"""Tests for space access grant and ingestion set helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uqadm.space.access_grant import cmd_space_access_grant
from uqadm.space.ingestion_set import cmd_space_ingestion_set


def _cfg() -> MagicMock:
    return MagicMock(user_id="u1", company_id="c1")


def test_space_access_grant_requires_principal() -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_space_access_grant(
            _cfg(),
            space_id="asst_1",
            group_ids=(),
            user_ids=(),
            access_type="USE",
        )
    assert ei.value.code == 2


@patch("uqadm.space.access_grant.Space.add_space_access")
def test_space_access_grant_groups_and_users(mock_add: MagicMock) -> None:
    cmd_space_access_grant(
        _cfg(),
        space_id="asst_1",
        group_ids=("g1",),
        user_ids=("u9",),
        access_type="MANAGE",
    )
    mock_add.assert_called_once_with(
        "u1",
        "c1",
        "asst_1",
        access=[
            {"entityId": "g1", "entityType": "GROUP", "type": "MANAGE"},
            {"entityId": "u9", "entityType": "USER", "type": "MANAGE"},
        ],
    )


@patch("uqadm.space.ingestion_set.Space.update_space")
@patch("uqadm.space.ingestion_set.Space.get_space")
def test_space_ingestion_set_merges_settings(
    mock_get: MagicMock,
    mock_up: MagicMock,
    tmp_path: Path,
) -> None:
    mock_get.return_value = {
        "settings": {"deviceAvailability": "ALL", "ingestionConfig": {"old": True}},
    }
    p = tmp_path / "ing.yaml"
    p.write_text("chunkStrategy: fixed\n", encoding="utf-8")
    cmd_space_ingestion_set(
        _cfg(),
        space_id="asst_x",
        config_path=p,
        dry_run=False,
    )
    mock_up.assert_called_once_with(
        "u1",
        "c1",
        "asst_x",
        settings={
            "deviceAvailability": "ALL",
            "ingestionConfig": {"chunkStrategy": "fixed"},
        },
    )


@patch("uqadm.space.ingestion_set.Space.update_space")
@patch("uqadm.space.ingestion_set.Space.get_space")
def test_space_ingestion_dry_run_skips_patch(
    mock_get: MagicMock,
    mock_up: MagicMock,
    tmp_path: Path,
) -> None:
    mock_get.return_value = {"settings": None}
    p = tmp_path / "ing.json"
    p.write_text("{}", encoding="utf-8")
    cmd_space_ingestion_set(
        _cfg(),
        space_id="asst_x",
        config_path=p,
        dry_run=True,
    )
    mock_up.assert_not_called()
