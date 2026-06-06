"""Tests for ``uqadm kb`` command helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uqadm.kb.access import cmd_access_grant
from uqadm.kb.ingestion import cmd_ingestion_set
from uqadm.kb.mkdir import cmd_mkdir


def _cfg() -> MagicMock:
    return MagicMock(user_id="u1", company_id="c1")


def test_mkdir_exits_when_no_paths() -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_mkdir(
            _cfg(),
            extra_paths=[],
            paths_file=None,
            parent_scope_id=None,
            inherit_access=True,
        )
    assert ei.value.code == 2


@patch("uqadm.kb.mkdir.Folder.create_paths")
def test_mkdir_calls_api_with_paths(mock_cp: MagicMock, tmp_path: Path) -> None:
    mock_cp.return_value = {"createdFolders": [{"id": "s1", "name": "n"}]}
    f = tmp_path / "p.txt"
    f.write_text("/A/B\n", encoding="utf-8")
    cmd_mkdir(
        _cfg(),
        extra_paths=("/X",),
        paths_file=f,
        parent_scope_id=None,
        inherit_access=False,
    )
    mock_cp.assert_called_once()
    call_kw = mock_cp.call_args[1]
    assert call_kw["paths"] == ["/A/B", "/X"]
    assert call_kw["inheritAccess"] is False


@patch("uqadm.kb.mkdir.Folder.create_paths")
def test_mkdir_parent_scope_relative(mock_cp: MagicMock) -> None:
    mock_cp.return_value = {"createdFolders": []}
    cmd_mkdir(
        _cfg(),
        extra_paths=("rel/a",),
        paths_file=None,
        parent_scope_id="parent_scope",
        inherit_access=True,
    )
    mock_cp.assert_called_once()
    kw = mock_cp.call_args[1]
    assert kw["parentScopeId"] == "parent_scope"
    assert kw["relativePaths"] == ["rel/a"]


@patch("uqadm.kb.access.Folder.add_access")
def test_access_grant_scope_and_groups(mock_aa: MagicMock) -> None:
    cmd_access_grant(
        _cfg(),
        folder_path=None,
        scope_id="sc1",
        group_ids=("g1", "g2"),
        permission="WRITE",
        apply_to_subfolders=True,
    )
    mock_aa.assert_called_once_with(
        "u1",
        "c1",
        scopeId="sc1",
        scopeAccesses=[
            {"entityId": "g1", "entityType": "GROUP", "type": "WRITE"},
            {"entityId": "g2", "entityType": "GROUP", "type": "WRITE"},
        ],
        applyToSubScopes=True,
    )


def test_access_grant_requires_folder_xor_scope() -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_access_grant(
            _cfg(),
            folder_path="/a",
            scope_id="s",
            group_ids=("g1",),
            permission="READ",
            apply_to_subfolders=True,
        )
    assert ei.value.code == 2


@patch("uqadm.kb.ingestion.Folder.update_ingestion_config")
def test_ingestion_set_from_file(mock_uic: MagicMock, tmp_path: Path) -> None:
    p = tmp_path / "ing.json"
    p.write_text('{"uniqueIngestionMode": "FULL"}', encoding="utf-8")
    cmd_ingestion_set(
        _cfg(),
        config_path=p,
        folder_path="/Docs",
        scope_id=None,
        apply_to_subfolders=False,
    )
    mock_uic.assert_called_once_with(
        "u1",
        "c1",
        ingestionConfig={"uniqueIngestionMode": "FULL"},
        applyToSubScopes=False,
        folderPath="/Docs",
    )


def test_access_grant_requires_groups() -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_access_grant(
            _cfg(),
            folder_path="/Docs",
            scope_id=None,
            group_ids=(),
            permission="READ",
            apply_to_subfolders=True,
        )
    assert ei.value.code == 2


@patch("uqadm.kb.access.Folder.add_access")
def test_access_grant_folder_path(mock_aa: MagicMock) -> None:
    cmd_access_grant(
        _cfg(),
        folder_path="/Docs",
        scope_id=None,
        group_ids=("g1",),
        permission="READ",
        apply_to_subfolders=False,
    )
    mock_aa.assert_called_once_with(
        "u1",
        "c1",
        folderPath="/Docs",
        scopeAccesses=[
            {"entityId": "g1", "entityType": "GROUP", "type": "READ"},
        ],
        applyToSubScopes=False,
    )


@patch("uqadm.kb.access.Folder.add_access", side_effect=RuntimeError("api down"))
def test_access_grant_api_failure(
    mock_aa: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_access_grant(
            _cfg(),
            folder_path="/Docs",
            scope_id=None,
            group_ids=("g1",),
            permission="READ",
            apply_to_subfolders=True,
        )
    assert ei.value.code == 1
    mock_aa.assert_called_once()
    err = capsys.readouterr().err
    assert "add_access failed" in err


@patch("uqadm.kb.mkdir.Folder.create_paths", side_effect=OSError("disk"))
def test_mkdir_api_failure(
    mock_cp: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_mkdir(
            _cfg(),
            extra_paths=("/X",),
            paths_file=None,
            parent_scope_id=None,
            inherit_access=True,
        )
    assert ei.value.code == 1
    assert "create_paths failed" in capsys.readouterr().err


@patch("uqadm.kb.mkdir.Folder.create_paths")
def test_mkdir_no_new_folders_message(
    mock_cp: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_cp.return_value = {"createdFolders": []}
    cmd_mkdir(
        _cfg(),
        extra_paths=("/exists",),
        paths_file=None,
        parent_scope_id=None,
        inherit_access=True,
    )
    assert "No new folders" in capsys.readouterr().out


def test_ingestion_set_requires_folder_xor_scope() -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_set(
            _cfg(),
            config_path=Path("unused.json"),
            folder_path="/a",
            scope_id="s",
            apply_to_subfolders=True,
        )
    assert ei.value.code == 2


def test_ingestion_set_invalid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_set(
            _cfg(),
            config_path=p,
            folder_path="/Docs",
            scope_id=None,
            apply_to_subfolders=True,
        )
    assert ei.value.code == 2
    assert "Invalid JSON" in capsys.readouterr().err


def test_ingestion_set_invalid_yaml(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("key: [unclosed", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_set(
            _cfg(),
            config_path=p,
            folder_path="/Docs",
            scope_id=None,
            apply_to_subfolders=True,
        )
    assert ei.value.code == 2
    assert "Invalid YAML" in capsys.readouterr().err


def test_ingestion_set_non_mapping_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_set(
            _cfg(),
            config_path=p,
            folder_path="/Docs",
            scope_id=None,
            apply_to_subfolders=True,
        )
    assert ei.value.code == 2
    assert "mapping" in capsys.readouterr().err


@patch("uqadm.kb.ingestion.Folder.update_ingestion_config")
def test_ingestion_set_scope_id(mock_uic: MagicMock, tmp_path: Path) -> None:
    p = tmp_path / "ing.json"
    p.write_text("{}", encoding="utf-8")
    cmd_ingestion_set(
        _cfg(),
        config_path=p,
        folder_path=None,
        scope_id="scope_1",
        apply_to_subfolders=True,
    )
    mock_uic.assert_called_once_with(
        "u1",
        "c1",
        ingestionConfig={},
        applyToSubScopes=True,
        scopeId="scope_1",
    )


@patch(
    "uqadm.kb.ingestion.Folder.update_ingestion_config",
    side_effect=RuntimeError("fail"),
)
def test_ingestion_set_api_failure(
    mock_uic: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "ing.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_set(
            _cfg(),
            config_path=p,
            folder_path="/Docs",
            scope_id=None,
            apply_to_subfolders=False,
        )
    assert ei.value.code == 1
    assert "update_ingestion_config failed" in capsys.readouterr().err
