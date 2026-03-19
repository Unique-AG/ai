"""Tests for unique_sdk.cli.commands."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from unique_sdk.cli.commands.files import (
    _resolve_content_id,
    _resolve_upload_destination,
    cmd_download,
    cmd_mv_file,
    cmd_rm,
    cmd_upload,
)
from unique_sdk.cli.commands.folders import cmd_mkdir, cmd_mvdir, cmd_rmdir
from unique_sdk.cli.commands.navigation import cmd_cd, cmd_ls, cmd_pwd
from unique_sdk.cli.commands.search import (
    _build_metadata_filter,
    _resolve_folder_to_scope_id,
    cmd_search,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


def _state(path: str = "/", scope_id: str | None = None) -> ShellState:
    s = ShellState(_config())
    s._path = path
    s._scope_id = scope_id
    return s


def _folder_info(
    name: str = "Reports",
    fid: str = "scope_abc",
) -> dict[str, Any]:
    return {
        "id": fid,
        "name": name,
        "ingestionConfig": {},
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-03-01T10:00:00Z",
        "parentId": "scope_root",
    }


def _content_info(
    title: str = "report.pdf",
    cid: str = "cont_123",
) -> dict[str, Any]:
    return {
        "id": cid,
        "key": "report.pdf",
        "url": None,
        "title": title,
        "metadata": None,
        "mimeType": "application/pdf",
        "description": None,
        "byteSize": 1024,
        "ownerId": "user_1",
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-03-01T10:00:00Z",
    }


# --- Navigation ---


class TestNavigation:
    def test_pwd(self) -> None:
        assert cmd_pwd(_state()) == "/"
        assert cmd_pwd(_state("/Reports")) == "/Reports"

    @patch("unique_sdk.Folder.get_info")
    def test_cd(self, mock: MagicMock) -> None:
        mock.return_value = {"id": "scope_r"}
        result = cmd_cd(_state(), "Reports")
        assert result == "/Reports"

    def test_cd_root(self) -> None:
        result = cmd_cd(_state("/Reports", "scope_r"), "/")
        assert result == "/"

    @patch("unique_sdk.Folder.get_info")
    def test_cd_error(self, mock: MagicMock) -> None:
        mock.side_effect = ValueError("not found")
        result = cmd_cd(_state(), "Nonexistent")
        assert "cd:" in result

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    def test_ls_root(self, mock_folders: MagicMock, mock_files: MagicMock) -> None:
        mock_folders.return_value = {
            "folderInfos": [_folder_info()],
            "totalCount": 1,
        }
        mock_files.return_value = {
            "contentInfos": [_content_info()],
            "totalCount": 1,
        }
        result = cmd_ls(_state())
        assert "DIR" in result
        assert "Reports/" in result
        assert "FILE" in result
        assert "report.pdf" in result
        assert "1 folder(s), 1 file(s)" in result

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    def test_ls_with_target(
        self,
        mock_folders: MagicMock,
        mock_files: MagicMock,
    ) -> None:
        mock_folders.return_value = {"folderInfos": [], "totalCount": 0}
        mock_files.return_value = {"contentInfos": [], "totalCount": 0}
        with patch("unique_sdk.Folder.get_info") as mock_info:
            mock_info.return_value = {"id": "scope_r"}
            result = cmd_ls(_state(), "/Reports")
        assert "0 folder(s), 0 file(s)" in result

    @patch("unique_sdk.Folder.get_infos")
    def test_ls_error(self, mock: MagicMock) -> None:
        mock.side_effect = ValueError("bad")
        result = cmd_ls(_state())
        assert "ls:" in result


# --- Folders ---


class TestFolders:
    @patch("unique_sdk.Folder.create_paths")
    def test_mkdir(self, mock: MagicMock) -> None:
        mock.return_value = {"createdFolders": [{"id": "scope_new"}]}
        result = cmd_mkdir(_state("/Reports", "scope_r"), "Q2")
        assert "Created" in result
        assert "scope_new" in result

    @patch("unique_sdk.Folder.create_paths")
    def test_mkdir_no_created(self, mock: MagicMock) -> None:
        mock.return_value = {"createdFolders": []}
        result = cmd_mkdir(_state("/Reports", "scope_r"), "Q2")
        assert "Created" in result

    @patch("unique_sdk.Folder.create_paths")
    def test_mkdir_error(self, mock: MagicMock) -> None:
        mock.side_effect = ValueError("exists")
        result = cmd_mkdir(_state(), "X")
        assert "mkdir:" in result

    @patch("unique_sdk.Folder.delete")
    def test_rmdir_by_path(self, mock: MagicMock) -> None:
        result = cmd_rmdir(_state("/Reports", "scope_r"), "Q2")
        assert "Deleted folder" in result

    @patch("unique_sdk.Folder.delete")
    def test_rmdir_by_scope(self, mock: MagicMock) -> None:
        result = cmd_rmdir(_state(), "scope_abc", recursive=True)
        assert "Deleted folder" in result
        mock.assert_called_once_with(
            user_id="u1",
            company_id="c1",
            scopeId="scope_abc",
            recursive=True,
        )

    @patch("unique_sdk.Folder.delete")
    def test_rmdir_absolute_path(self, mock: MagicMock) -> None:
        result = cmd_rmdir(_state(), "/Reports/Q2")
        assert "Deleted folder" in result

    @patch("unique_sdk.Folder.delete")
    def test_rmdir_error(self, mock: MagicMock) -> None:
        mock.side_effect = ValueError("not empty")
        result = cmd_rmdir(_state(), "Q2")
        assert "rmdir:" in result

    @patch("unique_sdk.Folder.update")
    def test_mvdir(self, mock: MagicMock) -> None:
        mock.return_value = _folder_info(name="Q1-2025")
        result = cmd_mvdir(_state("/Reports", "scope_r"), "Q1", "Q1-2025")
        assert "Renamed folder" in result
        assert "Q1-2025" in result

    @patch("unique_sdk.Folder.update")
    def test_mvdir_by_scope(self, mock: MagicMock) -> None:
        mock.return_value = _folder_info(name="New")
        result = cmd_mvdir(_state(), "scope_abc", "New")
        assert "Renamed folder" in result
        mock.assert_called_once_with(
            user_id="u1",
            company_id="c1",
            scopeId="scope_abc",
            name="New",
        )

    @patch("unique_sdk.Folder.update")
    def test_mvdir_error(self, mock: MagicMock) -> None:
        mock.side_effect = ValueError("not found")
        result = cmd_mvdir(_state(), "Q1", "Q2")
        assert "mvdir:" in result


# --- Files ---


class TestFiles:
    @patch("unique_sdk.Content.get_infos")
    def test_resolve_content_id_by_id(self, mock: MagicMock) -> None:
        cid, name = _resolve_content_id(_state(), "cont_abc")
        assert cid == "cont_abc"
        assert name == "cont_abc"
        mock.assert_not_called()

    @patch("unique_sdk.Content.get_infos")
    def test_resolve_content_id_by_name(self, mock: MagicMock) -> None:
        mock.return_value = {"contentInfos": [_content_info()]}
        cid, name = _resolve_content_id(
            _state("/Reports", "scope_r"),
            "report.pdf",
        )
        assert cid == "cont_123"
        assert name == "report.pdf"

    @patch("unique_sdk.Content.get_infos")
    def test_resolve_content_id_not_found(self, mock: MagicMock) -> None:
        mock.return_value = {"contentInfos": []}
        with pytest.raises(ValueError, match="File not found"):
            _resolve_content_id(_state(), "nope.pdf")

    def test_resolve_upload_dest_none(self) -> None:
        scope, name = _resolve_upload_destination(
            _state("/R", "scope_r"),
            "file.pdf",
            None,
        )
        assert scope == "scope_r"
        assert name == "file.pdf"

    def test_resolve_upload_dest_dot(self) -> None:
        scope, name = _resolve_upload_destination(
            _state("/R", "scope_r"),
            "file.pdf",
            ".",
        )
        assert scope == "scope_r"
        assert name == "file.pdf"

    def test_resolve_upload_dest_none_at_root(self) -> None:
        with pytest.raises(ValueError, match="cannot upload to root"):
            _resolve_upload_destination(_state(), "file.pdf", None)

    def test_resolve_upload_dest_scope_id(self) -> None:
        scope, name = _resolve_upload_destination(
            _state(),
            "file.pdf",
            "scope_xyz",
        )
        assert scope == "scope_xyz"
        assert name == "file.pdf"

    def test_resolve_upload_dest_rename(self) -> None:
        scope, name = _resolve_upload_destination(
            _state("/R", "scope_r"),
            "file.pdf",
            "new.pdf",
        )
        assert scope == "scope_r"
        assert name == "new.pdf"

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_upload_dest_subfolder(self, mock: MagicMock) -> None:
        mock.return_value = {"id": "scope_sub"}
        scope, name = _resolve_upload_destination(
            _state("/R", "scope_r"),
            "file.pdf",
            "sub/",
        )
        assert scope == "scope_sub"
        assert name == "file.pdf"

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_upload_dest_subfolder_rename(self, mock: MagicMock) -> None:
        mock.return_value = {"id": "scope_sub"}
        scope, name = _resolve_upload_destination(
            _state("/R", "scope_r"),
            "file.pdf",
            "sub/new.pdf",
        )
        assert scope == "scope_sub"
        assert name == "new.pdf"

    def test_resolve_upload_dest_dot_subfolder(self) -> None:
        scope, name = _resolve_upload_destination(
            _state("/R", "scope_r"),
            "file.pdf",
            "./new.pdf",
        )
        assert scope == "scope_r"
        assert name == "new.pdf"

    @patch("unique_sdk.Content.delete")
    @patch("unique_sdk.Content.get_infos")
    def test_rm(self, mock_infos: MagicMock, mock_delete: MagicMock) -> None:
        mock_infos.return_value = {"contentInfos": [_content_info()]}
        result = cmd_rm(_state("/R", "scope_r"), "report.pdf")
        assert "Deleted" in result
        assert "cont_123" in result

    @patch("unique_sdk.Content.delete")
    def test_rm_by_id(self, mock_delete: MagicMock) -> None:
        result = cmd_rm(_state(), "cont_abc")
        assert "Deleted" in result

    @patch("unique_sdk.Content.delete")
    def test_rm_error(self, mock_delete: MagicMock) -> None:
        mock_delete.side_effect = ValueError("not found")
        result = cmd_rm(_state(), "cont_abc")
        assert "rm:" in result

    @patch("unique_sdk.Content.update")
    @patch("unique_sdk.Content.get_infos")
    def test_mv_file(self, mock_infos: MagicMock, mock_update: MagicMock) -> None:
        mock_infos.return_value = {"contentInfos": [_content_info()]}
        mock_update.return_value = _content_info(title="new.pdf")
        result = cmd_mv_file(_state("/R", "scope_r"), "report.pdf", "new.pdf")
        assert "Renamed" in result
        assert "new.pdf" in result

    @patch("unique_sdk.Content.update")
    def test_mv_file_error(self, mock: MagicMock) -> None:
        mock.side_effect = ValueError("fail")
        result = cmd_mv_file(_state(), "cont_abc", "new.pdf")
        assert "mv:" in result

    def test_upload_nonexistent_file(self) -> None:
        result = cmd_upload(_state("/R", "scope_r"), "/nonexistent/file.pdf")
        assert "local file not found" in result

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.cli.commands.files.upload_file")
    def test_upload_success(
        self,
        mock_upload: MagicMock,
        mock_path: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        f = tmp_path / "test.pdf"
        f.write_text("content")
        mock_result = MagicMock()
        mock_result.id = "cont_new"
        mock_upload.return_value = mock_result
        mock_path.return_value = {"folderPath": "/Reports"}
        result = cmd_upload(_state("/Reports", "scope_r"), str(f))
        assert "Uploaded" in result
        assert "cont_new" in result

    @patch("unique_sdk.cli.commands.files.shutil.move")
    @patch("unique_sdk.cli.commands.files.download_content")
    def test_download_by_id(
        self,
        mock_dl: MagicMock,
        mock_move: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        mock_dl.return_value = tmp_path / "downloaded"
        result = cmd_download(_state(), "cont_abc")
        assert "Downloaded" in result

    @patch("unique_sdk.cli.commands.files.shutil.move")
    @patch("unique_sdk.cli.commands.files.download_content")
    @patch("unique_sdk.Content.get_infos")
    def test_download_by_name(
        self,
        mock_infos: MagicMock,
        mock_dl: MagicMock,
        mock_move: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        mock_infos.return_value = {"contentInfos": [_content_info()]}
        mock_dl.return_value = tmp_path / "downloaded"
        result = cmd_download(
            _state("/R", "scope_r"),
            "report.pdf",
            str(tmp_path),
        )
        assert "Downloaded" in result

    @patch("unique_sdk.cli.commands.files.download_content")
    def test_download_error(self, mock_dl: MagicMock) -> None:
        mock_dl.side_effect = ValueError("fail")
        result = cmd_download(_state(), "cont_abc")
        assert "download:" in result


# --- Search ---


class TestSearch:
    def test_build_metadata_filter_none(self) -> None:
        assert _build_metadata_filter(None, None) is None

    def test_build_metadata_filter_folder_only(self) -> None:
        result = _build_metadata_filter("scope_abc", None)
        assert result is not None
        assert result["path"] == ["folderIdPath"]
        assert "scope_abc" in result["value"]

    def test_build_metadata_filter_metadata_only(self) -> None:
        result = _build_metadata_filter(None, [("dept", "Legal")])
        assert result is not None
        assert result["path"] == ["dept"]
        assert result["value"] == "Legal"

    def test_build_metadata_filter_combined(self) -> None:
        result = _build_metadata_filter("scope_abc", [("dept", "Legal")])
        assert result is not None
        assert "and" in result

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_folder_scope_id(self, mock: MagicMock) -> None:
        result = _resolve_folder_to_scope_id(_state(), "scope_abc")
        assert result == "scope_abc"
        mock.assert_not_called()

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_folder_path(self, mock: MagicMock) -> None:
        mock.return_value = {"id": "scope_r"}
        result = _resolve_folder_to_scope_id(_state(), "/Reports")
        assert result == "scope_r"

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_folder_relative(self, mock: MagicMock) -> None:
        mock.return_value = {"id": "scope_q1"}
        result = _resolve_folder_to_scope_id(
            _state("/Reports", "scope_r"),
            "Q1",
        )
        assert result == "scope_q1"
        mock.assert_called_once_with(
            user_id="u1",
            company_id="c1",
            folderPath="/Reports/Q1",
        )

    @patch("unique_sdk.Search.create")
    def test_cmd_search(self, mock: MagicMock) -> None:
        mock.return_value = []
        result = cmd_search(_state(), "query")
        assert "No results found" in result

    @patch("unique_sdk.Search.create")
    def test_cmd_search_with_scope(self, mock: MagicMock) -> None:
        mock.return_value = []
        result = cmd_search(_state("/R", "scope_r"), "query")
        assert "No results found" in result
        call_kwargs = mock.call_args[1]
        assert call_kwargs["scopeIds"] == ["scope_r"]

    @patch("unique_sdk.Search.create")
    def test_cmd_search_error(self, mock: MagicMock) -> None:
        mock.side_effect = ValueError("fail")
        result = cmd_search(_state(), "query")
        assert "search:" in result
