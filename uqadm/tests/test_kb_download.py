"""Unit tests for ``uqadm kb download`` (``cmd_download``)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from uqadm.kb.download import cmd_download


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(user_id="u1", company_id="c1")


def _no_content() -> dict[str, object]:
    return {"contentInfos": [], "totalCount": 0}


def _no_folders() -> dict[str, object]:
    return {"folderInfos": [], "totalCount": 0}


@patch("uqadm.kb.download.download_content")
@patch("uqadm.kb.download.Folder")
@patch("uqadm.kb.download.Content")
def test_single_file_downloaded(
    content: MagicMock,
    folder: MagicMock,
    download: MagicMock,
    tmp_path: Path,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [{"id": "cont_1", "key": "a.txt"}],
        "totalCount": 1,
    }
    out_dir = tmp_path / "out"

    cmd_download(
        _cfg(),
        local_dir=out_dir,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=False,
    )

    download.assert_called_once()
    kwargs = download.call_args.kwargs
    assert kwargs["content_id"] == "cont_1"
    assert kwargs["target_path"] == out_dir / "a.txt"


@patch("uqadm.kb.download.download_content")
@patch("uqadm.kb.download.Folder")
@patch("uqadm.kb.download.Content")
def test_recursive_downloads_nested_folder_files(
    content: MagicMock,
    folder: MagicMock,
    download: MagicMock,
    tmp_path: Path,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"

    def content_side_effect(
        user_id: str,
        company_id: str,
        **kwargs: object,
    ) -> dict[str, object]:
        parent_id = kwargs.get("parentId")
        if parent_id == "scope1":
            return {
                "contentInfos": [{"id": "cont_top", "key": "top.txt"}],
                "totalCount": 1,
            }
        if parent_id == "scope_sub":
            return {
                "contentInfos": [{"id": "cont_nested", "key": "nested.txt"}],
                "totalCount": 1,
            }
        return _no_content()

    content.get_infos.side_effect = content_side_effect

    def folder_side_effect(
        user_id: str,
        company_id: str,
        **kwargs: object,
    ) -> dict[str, object]:
        parent_id = kwargs.get("parentId")
        if parent_id == "scope1":
            return {
                "folderInfos": [{"id": "scope_sub", "name": "sub"}],
                "totalCount": 1,
            }
        return _no_folders()

    folder.get_infos.side_effect = folder_side_effect
    out_dir = tmp_path / "out"

    cmd_download(
        _cfg(),
        local_dir=out_dir,
        folder_path="/X",
        scope_id=None,
        recursive=True,
        dry_run=False,
    )

    assert download.call_count == 2
    paths = {call.kwargs["target_path"] for call in download.call_args_list}
    assert out_dir / "top.txt" in paths
    assert out_dir / "sub" / "nested.txt" in paths


@patch("uqadm.kb.download.download_content")
@patch("uqadm.kb.download.Folder")
@patch("uqadm.kb.download.Content")
def test_dry_run_does_not_download(
    content: MagicMock,
    folder: MagicMock,
    download: MagicMock,
    tmp_path: Path,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [{"id": "cont_1", "key": "a.txt"}],
        "totalCount": 1,
    }
    out_dir = tmp_path / "out"

    cmd_download(
        _cfg(),
        local_dir=out_dir,
        folder_path="/X",
        scope_id=None,
        recursive=False,
        dry_run=True,
    )

    download.assert_not_called()
    assert not out_dir.exists()


def test_missing_target_selector_exits_2(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_download(
            _cfg(),
            local_dir=tmp_path,
            folder_path=None,
            scope_id=None,
            recursive=False,
            dry_run=False,
        )
    assert exc.value.code == 2


@patch("uqadm.kb.download.download_content")
@patch("uqadm.kb.download.Folder")
@patch("uqadm.kb.download.Content")
def test_partial_failure_exits_1(
    content: MagicMock,
    folder: MagicMock,
    download: MagicMock,
    tmp_path: Path,
) -> None:
    folder.resolve_scope_id_from_folder_path.return_value = "scope1"
    content.get_infos.return_value = {
        "contentInfos": [
            {"id": "cont_ok", "key": "ok.txt"},
            {"id": "cont_bad", "key": "bad.txt"},
        ],
        "totalCount": 2,
    }
    download.side_effect = [Path(tmp_path / "ok.txt"), Exception("network error")]
    out_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exc:
        cmd_download(
            _cfg(),
            local_dir=out_dir,
            folder_path="/X",
            scope_id=None,
            recursive=False,
            dry_run=False,
        )
    assert exc.value.code == 1


@patch("uqadm.kb.download.download_content")
@patch("uqadm.kb.download.Folder")
@patch("uqadm.kb.download.Content")
def test_scope_id_entry_point(
    content: MagicMock,
    folder: MagicMock,
    download: MagicMock,
    tmp_path: Path,
) -> None:
    content.get_infos.return_value = {
        "contentInfos": [{"id": "cont_1", "key": "doc.pdf"}],
        "totalCount": 1,
    }
    out_dir = tmp_path / "out"

    cmd_download(
        _cfg(),
        local_dir=out_dir,
        folder_path=None,
        scope_id="scope_abc",
        recursive=False,
        dry_run=False,
    )

    folder.resolve_scope_id_from_folder_path.assert_not_called()
    download.assert_called_once()
    assert download.call_args.kwargs["content_id"] == "cont_1"
