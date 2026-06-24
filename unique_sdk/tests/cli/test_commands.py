"""Tests for unique_sdk.cli.commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import unique_sdk
from unique_sdk.cli.commands.files import (
    _detect_upload_mime_type,
    _resolve_content_id,
    _resolve_upload_destination,
    cmd_download,
    cmd_mv_file,
    cmd_restore_version,
    cmd_rm,
    cmd_upload,
    cmd_versions,
)
from unique_sdk.cli.commands.folders import cmd_mkdir, cmd_mvdir, cmd_rmdir
from unique_sdk.cli.commands.mcp import _parse_and_validate, _read_payload, cmd_mcp
from unique_sdk.cli.commands.navigation import cmd_cd, cmd_ls, cmd_pwd
from unique_sdk.cli.commands.scheduled_tasks import (
    cmd_schedule_create,
    cmd_schedule_delete,
    cmd_schedule_get,
    cmd_schedule_list,
    cmd_schedule_update,
)
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


class TestIsPermissionDeniedOutput:
    def test_denial_lines_detected(self) -> None:
        from unique_sdk.cli.commands.files import is_permission_denied_output

        for out in (
            "upload: permission denied (outside workspace scope)",
            "upload: permission denied: destination is outside your task scope.",
            "restore-version: permission denied: cannot verify the target.",
            "ls: permission denied: target is outside your task scope.",
            "download: permission denied: cont_x is outside your task scope.",
        ):
            assert is_permission_denied_output(out), out

    def test_success_containing_phrase_not_flagged(self) -> None:
        from unique_sdk.cli.commands.files import is_permission_denied_output

        # A successful result must not exit non-zero just because its text
        # contains the phrase (e.g. a filename). Successes are capitalised.
        for out in (
            'Uploaded: "permission denied.pdf" (cont_1) to /Reports',
            "Downloaded: permission denied notes.txt -> /tmp/x",
            "Renamed permission denied.pdf",
            # A multi-line success whose *later* line happens to start with a
            # lowercase token + ": permission denied" must NOT be flagged: the
            # regex anchors at the start of the string only (no re.MULTILINE),
            # so only a result that *begins* with the denial shape counts.
            "Downloaded: report.pdf -> /tmp/x\nfoo: permission denied (in body)",
        ):
            assert not is_permission_denied_output(out), out


def _folder_path_side_effect(mapping: dict[str, str]):  # type: ignore[no-untyped-def]
    """Side effect for Folder.get_folder_path mapping scope_id -> folderPath."""

    def _inner(*, user_id, company_id, scope_id):  # type: ignore[no-untyped-def]
        if scope_id in mapping:
            return {"folderPath": mapping[scope_id]}
        raise Exception(f"folder not found: {scope_id}")

    return _inner


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

    @patch("unique_sdk.Folder.get_info")
    def test_ls_root_workspace_scoped(self, mock_info: MagicMock) -> None:
        """ls at root with workspace scopes shows only the allowed folders."""
        mock_info.return_value = _folder_info("Reports", "scope_ws")
        state = _state()
        state.workspace_scope_ids = ["scope_ws"]
        result = cmd_ls(state)
        assert "Reports/" in result
        assert "1 folder(s), 0 file(s)" in result
        mock_info.assert_called_once_with(
            user_id="u1",
            company_id="c1",
            scopeId="scope_ws",
        )

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    def test_ls_inside_folder_workspace_scoped_uses_normal_path(
        self,
        mock_folders: MagicMock,
        mock_files: MagicMock,
    ) -> None:
        """ls inside a scoped folder uses the normal get_infos path."""
        mock_folders.return_value = {"folderInfos": [], "totalCount": 0}
        mock_files.return_value = {"contentInfos": [], "totalCount": 0}
        state = _state("/Reports", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        result = cmd_ls(state)
        assert "0 folder(s), 0 file(s)" in result
        mock_folders.assert_called_once()

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_info")
    def test_ls_root_metadata_filter_scoped(
        self,
        mock_folder: MagicMock,
        mock_content: MagicMock,
        mock_path: MagicMock,
    ) -> None:
        """ls at root with a per-message filter shows only its folders + docs.

        The doc is shown only because it satisfies the *full* AND filter (it
        lives in Fund A); root ls verifies this via is_content_within_workspace.
        """
        mock_folder.return_value = _folder_info("Fund A", "scope_fund_a")
        # cont_1's owner folder resolves into Fund A, so the AND filter holds.
        info = _content_info("memo.pdf", "cont_1")
        info["ownerId"] = "scope_fund_a"
        mock_content.return_value = {"contentInfo": [info]}
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A"}
        )
        state = _state()
        # Static scope present but the per-message filter takes precedence.
        state.workspace_scope_ids = ["scope_broad"]
        state.workspace_metadata_filter = {
            "and": [
                {
                    "path": ["folderIdPath"],
                    "operator": "contains",
                    "value": "uniquepathid://scope_root/scope_fund_a",
                },
                {
                    "path": ["contentId"],
                    "operator": "in",
                    "value": ["cont_1"],
                },
            ]
        }
        result = cmd_ls(state)
        assert "Fund A/" in result
        assert "memo.pdf" in result
        assert "in task scope" in result
        mock_folder.assert_called_once_with(
            user_id="u1", company_id="c1", scopeId="scope_fund_a"
        )
        assert mock_content.call_args.kwargs["contentId"] == "cont_1"

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_info")
    def test_ls_root_hides_contentid_excluded_by_and(
        self,
        mock_folder: MagicMock,
        mock_content: MagicMock,
        mock_path: MagicMock,
    ) -> None:
        """Regression: a contentId in the filter that the *full* AND filter
        excludes (its owner folder is outside the required scope) must not have
        its title listed at root — read/cite and in-folder ls already deny it.
        See UN-21780.
        """
        mock_folder.return_value = _folder_info("Fund A", "scope_fund_a")
        # cont_x is named by the contentId leaf but lives outside Fund A.
        info = _content_info("secret.pdf", "cont_x")
        info["ownerId"] = "scope_other"
        mock_content.return_value = {"contentInfo": [info]}
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A", "scope_other": "/Other"}
        )
        state = _state()
        state.workspace_metadata_filter = {
            "and": [
                {
                    "path": ["folderIdPath"],
                    "operator": "contains",
                    "value": "uniquepathid://scope_root/scope_fund_a",
                },
                {
                    "path": ["contentId"],
                    "operator": "in",
                    "value": ["cont_x"],
                },
            ]
        }
        result = cmd_ls(state)
        assert "secret.pdf" not in result
        assert "0 file(s)" in result.split("folder(s),")[1]

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    def test_ls_target_outside_metadata_filter_denied(
        self,
        mock_folders: MagicMock,
        mock_files: MagicMock,
        mock_path: MagicMock,
    ) -> None:
        """A non-root ls target outside the per-message scope is denied."""

        def path_for(*args: Any, **kwargs: Any) -> dict[str, Any]:
            scope = kwargs.get("scope_id")
            return {
                "folderPath": {
                    "scope_fund_a": "/Funds/Fund A",
                    "scope_outside": "/Other",
                }.get(scope, "")
            }

        mock_path.side_effect = path_for
        state = _state("/Other", "scope_outside")
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_fund_a",
        }
        result = cmd_ls(state)
        assert "permission denied" in result
        mock_folders.assert_not_called()
        mock_files.assert_not_called()

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    def test_ls_target_inside_metadata_filter_allowed(
        self,
        mock_folders: MagicMock,
        mock_files: MagicMock,
        mock_path: MagicMock,
    ) -> None:
        def path_for(*args: Any, **kwargs: Any) -> dict[str, Any]:
            scope = kwargs.get("scope_id")
            return {
                "scope_fund_a": {"folderPath": "/Funds/Fund A"},
                "scope_sub": {"folderPath": "/Funds/Fund A/Sub"},
            }.get(scope, {"folderPath": ""})

        mock_path.side_effect = path_for
        mock_folders.return_value = {"folderInfos": [], "totalCount": 0}
        mock_files.return_value = {"contentInfos": [], "totalCount": 0}
        state = _state("/Funds/Fund A/Sub", "scope_sub")
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_fund_a",
        }
        result = cmd_ls(state)
        assert "permission denied" not in result
        mock_folders.assert_called_once()

    @patch("unique_sdk.Content.get_info")
    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    def test_ls_inside_folder_filters_files_to_allowlist(
        self,
        mock_folders: MagicMock,
        mock_files: MagicMock,
        mock_path: MagicMock,
        mock_info: MagicMock,
    ) -> None:
        """A combined folder + contentId filter must hide non-allowlisted
        files even when listing inside the allowed folder (UN-21780).
        """

        def path_for(*args: Any, **kwargs: Any) -> dict[str, Any]:
            scope = kwargs.get("scope_id")
            return {
                "scope_fund_a": {"folderPath": "/Funds/Fund A"},
                "scope_owner": {"folderPath": "/Funds/Fund A"},
            }.get(scope, {"folderPath": ""})

        mock_path.side_effect = path_for
        # Both files live in the allowed folder; only the allowlisted one
        # should survive the contentId leaf of the AND filter.
        mock_info.return_value = {"contentInfo": [{"ownerId": "scope_owner"}]}
        mock_folders.return_value = {"folderInfos": [], "totalCount": 0}
        mock_files.return_value = {
            "contentInfos": [
                _content_info("allowed.pdf", "cont_allowed"),
                _content_info("blocked.pdf", "cont_blocked"),
            ],
            "totalCount": 2,
        }
        state = _state("/Funds/Fund A", "scope_fund_a")
        state._chat_file_content_ids_cache = set()
        state.workspace_metadata_filter = {
            "and": [
                {
                    "path": ["folderIdPath"],
                    "operator": "contains",
                    "value": "scope_fund_a",
                },
                {
                    "path": ["contentId"],
                    "operator": "in",
                    "value": ["cont_allowed"],
                },
            ]
        }
        result = cmd_ls(state)
        assert "allowed.pdf" in result
        assert "blocked.pdf" not in result
        # The in-scope count is for the current page; the folder's real total
        # (from the API totalCount) is preserved as "(of N in folder)" rather
        # than being overwritten by the filtered page length. See UN-21780.
        assert "1 file(s) in task scope (of 2 in folder)" in result


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

    def test_mkdir_outside_workspace_blocked(self) -> None:
        state = _state()
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_mkdir(state, "Q2")
        assert "permission denied" in result

    def test_mkdir_dotdot_traversal_blocked(self) -> None:
        state = _state("/Workspace/Reports", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_mkdir(state, "../../outside")
        assert "permission denied" in result

    @patch("unique_sdk.Folder.get_folder_path")
    def test_rmdir_scope_id_outside_workspace_blocked(
        self, mock_path: MagicMock
    ) -> None:
        """rmdir scope_other blocked even when CWD is inside the workspace."""
        mock_path.return_value = {"folderPath": "/OtherTenant/Folder"}
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_rmdir(state, "scope_other")
        assert "permission denied" in result

    def test_rmdir_absolute_path_outside_workspace_blocked(self) -> None:
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_rmdir(state, "/OtherTenant/Folder")
        assert "permission denied" in result

    @patch("unique_sdk.Folder.get_folder_path")
    def test_mvdir_scope_id_outside_workspace_blocked(
        self, mock_path: MagicMock
    ) -> None:
        """mvdir scope_other blocked even when CWD is inside the workspace."""
        mock_path.return_value = {"folderPath": "/OtherTenant/Folder"}
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_mvdir(state, "scope_other", "new")
        assert "permission denied" in result

    def test_mvdir_absolute_path_outside_workspace_blocked(self) -> None:
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_mvdir(state, "/OtherTenant/Folder", "new")
        assert "permission denied" in result


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
    def test_resolve_by_name_gated_by_metadata_filter(self, mock: MagicMock) -> None:
        """Resolving by file name must not bypass the per-message scope.

        The cont_ fast-path checks is_content_within_workspace; the name/path
        resolution path must gate the *resolved* id the same way (UN-21780).
        """
        mock.return_value = {"contentInfos": [_content_info()]}
        s = _state("/Reports", "scope_r")
        s.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_allowed_only"],
        }
        s._chat_file_content_ids_cache = set()
        with pytest.raises(ValueError, match="permission denied"):
            _resolve_content_id(s, "report.pdf")

    @patch("unique_sdk.Content.get_infos")
    def test_resolve_by_name_at_root_with_filter_refuses_whole_kb_scan(
        self, mock: MagicMock
    ) -> None:
        """At the KB root (no folder context) a bare file name would resolve via
        an unparented whole-KB scan. With a per-message filter active that is a
        cross-scope existence/title oracle, so it must be refused *before* any
        Content.get_infos call rather than scan everything and gate per id. See
        UN-21780.
        """
        s = _state("/", None)
        s.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_allowed_only"],
        }
        s._chat_file_content_ids_cache = set()
        with pytest.raises(ValueError, match="permission denied"):
            _resolve_content_id(s, "report.pdf")
        mock.assert_not_called()

    @patch("unique_sdk.Content.delete")
    def test_rm_denies_out_of_scope_chat_attachment(
        self, mock_delete: MagicMock
    ) -> None:
        """A chat attachment outside the task scope is read-exempt but must not
        be deletable via that exemption. See UN-21780.
        """
        s = _state("/Reports", "scope_r")
        s.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_in_scope"],
        }
        s._chat_file_content_ids_cache = {"cont_attached"}
        # Read-exempt...
        assert s.is_content_within_workspace("cont_attached")
        # ...but rm is denied.
        result = cmd_rm(s, "cont_attached")
        assert "permission denied" in result
        mock_delete.assert_not_called()

    @patch("unique_sdk.Content.delete")
    @patch("unique_sdk.Content.get_infos")
    def test_rm_by_name_denies_out_of_scope_chat_attachment(
        self, mock_infos: MagicMock, mock_delete: MagicMock
    ) -> None:
        """Resolving by file name must honour the same read-only exemption —
        rm <name> can't reach an out-of-scope chat attachment. See UN-21780.
        """
        mock_infos.return_value = {
            "contentInfos": [_content_info("attached.pdf", "cont_attached")]
        }
        s = _state("/Reports", "scope_r")
        s.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_in_scope"],
        }
        s._chat_file_content_ids_cache = {"cont_attached"}
        result = cmd_rm(s, "attached.pdf")
        assert "permission denied" in result
        mock_delete.assert_not_called()

    @patch("unique_sdk.Content.update")
    def test_mv_denies_out_of_scope_chat_attachment(
        self, mock_update: MagicMock
    ) -> None:
        s = _state("/Reports", "scope_r")
        s.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_in_scope"],
        }
        s._chat_file_content_ids_cache = {"cont_attached"}
        result = cmd_mv_file(s, "cont_attached", "renamed.pdf")
        assert "permission denied" in result
        mock_update.assert_not_called()

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_info")
    def test_resolve_by_path_in_filter_not_blocked_by_static_scope(
        self, mock_finfo: MagicMock, mock_cinfos: MagicMock
    ) -> None:
        """An active per-message filter replaces the static scopeIds for content
        access, so a path lookup to an in-filter folder outside the static
        scope must resolve (the resolved id is gated by the filter). See
        UN-21780.
        """
        mock_finfo.return_value = {"id": "scope_allowed"}
        mock_cinfos.return_value = {
            "contentInfos": [_content_info("memo.pdf", "cont_1")]
        }
        s = _state("/", None)
        s.workspace_scope_ids = ["scope_admin"]
        s._workspace_scope_paths = ["/Admin"]
        s.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_1"],
        }
        s._chat_file_content_ids_cache = set()
        cid, name = _resolve_content_id(s, "/Funds/Fund A/memo.pdf")
        assert cid == "cont_1"
        assert name == "memo.pdf"

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_info")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_resolve_by_path_out_of_filter_folder_denied_without_lookup(
        self,
        mock_fpath: MagicMock,
        mock_finfo: MagicMock,
        mock_cinfos: MagicMock,
    ) -> None:
        """A path into a folder outside the per-message filter scope is denied
        structurally — before Folder.get_info or the name scan — so a matching
        out-of-scope file can't leak its existence (task-scope permission denied
        vs File not found). See UN-21780.
        """
        mock_fpath.return_value = {"folderPath": "/Allowed"}
        s = _state("/", None)
        s.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        s._chat_file_content_ids_cache = set()
        with pytest.raises(ValueError, match="permission denied"):
            _resolve_content_id(s, "/Outside/secret.pdf")
        mock_finfo.assert_not_called()
        mock_cinfos.assert_not_called()

    @patch("unique_sdk.Content.get_infos")
    def test_resolve_by_name_allowed_by_metadata_filter(self, mock: MagicMock) -> None:
        mock.return_value = {"contentInfos": [_content_info()]}
        s = _state("/Reports", "scope_r")
        s.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_123"],
        }
        s._chat_file_content_ids_cache = set()
        cid, name = _resolve_content_id(s, "report.pdf")
        assert cid == "cont_123"
        assert name == "report.pdf"

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_info")
    def test_resolve_content_id_by_absolute_path(
        self,
        mock_folder: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_folder.return_value = {"id": "scope_q1"}
        mock_content.return_value = {"contentInfos": [_content_info()]}
        cid, name = _resolve_content_id(
            _state("/Reports", "scope_r"),
            "/Reports/Q1/report.pdf",
        )
        assert cid == "cont_123"
        assert name == "report.pdf"
        assert mock_folder.call_args.kwargs["folderPath"] == "/Reports/Q1"
        assert mock_content.call_args.kwargs["parentId"] == "scope_q1"
        assert mock_content.call_args.kwargs["skip"] == 0
        assert mock_content.call_args.kwargs["take"] == 100

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_info")
    def test_resolve_content_id_by_relative_path(
        self,
        mock_folder: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_folder.return_value = {"id": "scope_q1"}
        mock_content.return_value = {"contentInfos": [_content_info()]}
        cid, name = _resolve_content_id(
            _state("/Reports", "scope_r"),
            "Q1/report.pdf",
        )
        assert cid == "cont_123"
        assert name == "report.pdf"
        assert mock_folder.call_args.kwargs["folderPath"] == "/Reports/Q1"

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_info")
    def test_resolve_content_id_normalizes_dot_path(
        self,
        mock_folder: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_folder.return_value = {"id": "scope_q1"}
        mock_content.return_value = {"contentInfos": [_content_info()]}
        cid, name = _resolve_content_id(
            _state("/Reports", "scope_r"),
            "./Q1/report.pdf",
        )
        assert cid == "cont_123"
        assert name == "report.pdf"
        assert mock_folder.call_args.kwargs["folderPath"] == "/Reports/Q1"

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_info")
    def test_resolve_content_id_normalizes_dot_dot_path(
        self,
        mock_folder: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_folder.return_value = {"id": "scope_q1"}
        mock_content.return_value = {"contentInfos": [_content_info()]}
        cid, name = _resolve_content_id(
            _state("/Reports/Q2", "scope_q2"),
            "../Q1/report.pdf",
        )
        assert cid == "cont_123"
        assert name == "report.pdf"
        assert mock_folder.call_args.kwargs["folderPath"] == "/Reports/Q1"

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_content_id_rejects_paths_above_root(
        self,
        mock_folder: MagicMock,
    ) -> None:
        with pytest.raises(ValueError, match="escapes root"):
            _resolve_content_id(_state("/Reports", "scope_r"), "../../secret.pdf")
        mock_folder.assert_not_called()

    @patch("unique_sdk.Content.get_infos")
    def test_resolve_content_id_scans_paginated_files(self, mock: MagicMock) -> None:
        other = _content_info(title="other.pdf")
        other["key"] = "other.pdf"
        mock.side_effect = [
            {"contentInfos": [other], "totalCount": 2},
            {"contentInfos": [_content_info()], "totalCount": 2},
        ]
        cid, name = _resolve_content_id(_state("/Reports", "scope_r"), "report.pdf")
        assert cid == "cont_123"
        assert name == "report.pdf"
        assert mock.call_args_list[0].kwargs["skip"] == 0
        assert mock.call_args_list[1].kwargs["skip"] == 1

    @patch("unique_sdk.Content.get_infos")
    def test_resolve_content_id_ignores_total_count_for_pagination(
        self,
        mock: MagicMock,
    ) -> None:
        other = _content_info(title="other.pdf")
        other["key"] = "other.pdf"
        mock.side_effect = [
            {"contentInfos": [other], "totalCount": 1},
            {"contentInfos": [], "totalCount": 1},
        ]
        with pytest.raises(ValueError, match="File not found"):
            _resolve_content_id(_state("/Reports", "scope_r"), "report.pdf")
        assert mock.call_args_list[0].kwargs["skip"] == 0
        assert mock.call_args_list[1].kwargs["skip"] == 1

    @patch("unique_sdk.Content.get_infos")
    def test_resolve_content_id_matches_storage_key(self, mock: MagicMock) -> None:
        mock.return_value = {
            "contentInfos": [_content_info(title="Display Name.pdf")],
            "totalCount": 1,
        }
        cid, name = _resolve_content_id(_state("/Reports", "scope_r"), "report.pdf")
        assert cid == "cont_123"
        assert name == "Display Name.pdf"

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

    def test_resolve_upload_dest_slash_only(self) -> None:
        """'/' strips to empty folder_path; must not fall through as relative cwd."""
        with pytest.raises(ValueError, match="cannot upload to root"):
            _resolve_upload_destination(_state("/R", "scope_r"), "file.pdf", "/")
        with pytest.raises(ValueError, match="cannot upload to root"):
            _resolve_upload_destination(_state("/R", "scope_r"), "file.pdf", "///")

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

    def test_upload_outside_workspace_blocked(self) -> None:
        state = _state()
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_upload(state, "/some/file.pdf")
        assert "permission denied" in result

    def test_upload_dotdot_destination_blocked(self) -> None:
        state = _state("/Workspace/Reports", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_upload(state, "/some/file.pdf", "../../outside/")
        assert "permission denied" in result

    @patch("unique_sdk.Folder.get_folder_path")
    def test_upload_scope_id_outside_workspace_blocked(
        self, mock_path: MagicMock
    ) -> None:
        """upload to explicit scope_other blocked even when CWD is inside the workspace."""
        mock_path.return_value = {"folderPath": "/OtherTenant/Folder"}
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_upload(state, "/some/file.pdf", "scope_other")
        assert "permission denied" in result

    def test_rm_outside_workspace_blocked(self) -> None:
        state = _state()
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_rm(state, "cont_abc")
        assert "permission denied" in result

    @patch("unique_sdk.Content.get_info")
    def test_rm_content_id_outside_workspace_blocked(
        self, mock_info: MagicMock
    ) -> None:
        """rm cont_X is blocked when the content's ownerId is outside the workspace,
        even when CWD is inside the workspace."""
        mock_info.return_value = {"contentInfo": [{"ownerId": "scope_other_tenant"}]}
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_rm(state, "cont_outside")
        assert "permission denied" in result

    @patch("unique_sdk.Content.delete")
    @patch("unique_sdk.Content.get_info")
    def test_rm_content_id_within_workspace_allowed(
        self, mock_info: MagicMock, mock_delete: MagicMock
    ) -> None:
        mock_info.return_value = {"contentInfo": [{"ownerId": "scope_ws"}]}
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_rm(state, "cont_inside")
        assert "permission denied" not in result

    def test_mv_file_outside_workspace_blocked(self) -> None:
        state = _state()
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_mv_file(state, "cont_abc", "new.pdf")
        assert "permission denied" in result

    @patch("unique_sdk.Content.get_info")
    def test_mv_file_content_id_outside_workspace_blocked(
        self, mock_info: MagicMock
    ) -> None:
        """mv cont_X is blocked when the content's ownerId is outside the workspace,
        even when CWD is inside the workspace."""
        mock_info.return_value = {"contentInfo": [{"ownerId": "scope_other_tenant"}]}
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_mv_file(state, "cont_outside", "new.pdf")
        assert "permission denied" in result

    def test_upload_nonexistent_file(self) -> None:
        result = cmd_upload(_state("/R", "scope_r"), "/nonexistent/file.pdf")
        assert "local file not found" in result

    @pytest.mark.parametrize(
        ("filename", "expected_mime_type"),
        [
            ("test.pdf", "application/pdf"),
            (
                "test.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            (
                "test.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                "test.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            ("test.txt", "text/plain"),
            ("test.html", "text/html"),
            ("test.md", "text/markdown"),
        ],
    )
    @patch("unique_sdk.cli.commands.files.mimetypes.guess_type")
    def test_detect_upload_mime_type_uses_supported_format_mapping(
        self,
        mock_guess_type: MagicMock,
        filename: str,
        expected_mime_type: str,
    ) -> None:
        mock_guess_type.return_value = (None, None)

        assert _detect_upload_mime_type(Path(filename)) == expected_mime_type
        mock_guess_type.assert_not_called()

    @patch("unique_sdk.cli.commands.files.mimetypes.guess_type")
    def test_detect_upload_mime_type_falls_back_to_guess_type(
        self,
        mock_guess_type: MagicMock,
    ) -> None:
        mock_guess_type.return_value = ("image/png", None)

        assert _detect_upload_mime_type(Path("test.png")) == "image/png"

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
        assert mock_upload.call_args.kwargs["versioning_enabled"] is True

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.cli.commands.files.upload_file")
    def test_upload_blocked_by_metadata_filter_without_scope_ids(
        self,
        mock_upload: MagicMock,
        mock_path: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        """A per-message metaDataFilter (no static scopeIds) must gate the
        upload destination, not leave it unrestricted (UN-21780).
        """
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A"}
        )
        f = tmp_path / "test.pdf"
        f.write_text("content")
        state = _state("/Other", "scope_other")
        # No static scopeIds, only a per-message folder filter.
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_upload(state, str(f), "scope_other")
        assert "permission denied" in result
        mock_upload.assert_not_called()

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.cli.commands.files.upload_file")
    def test_upload_allowed_by_metadata_filter(
        self,
        mock_upload: MagicMock,
        mock_path: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A"}
        )
        f = tmp_path / "test.pdf"
        f.write_text("content")
        mock_result = MagicMock()
        mock_result.id = "cont_new"
        mock_upload.return_value = mock_result
        state = _state("/Funds/Fund A", "scope_allowed")
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_upload(state, str(f), "scope_allowed")
        assert "Uploaded" in result
        mock_upload.assert_called_once()

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.cli.commands.files.upload_file")
    def test_upload_in_filter_not_blocked_by_static_scope(
        self,
        mock_upload: MagicMock,
        mock_path: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        """An active per-message filter replaces the static scopeIds, so an
        in-filter upload destination outside the static scope must not be
        over-denied by the static-scope check. See UN-21780.
        """
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A"}
        )
        f = tmp_path / "test.pdf"
        f.write_text("content")
        mock_result = MagicMock()
        mock_result.id = "cont_new"
        mock_upload.return_value = mock_result
        state = _state("/Funds/Fund A", "scope_allowed")
        state.workspace_scope_ids = ["scope_admin"]
        state._workspace_scope_paths = ["/Admin"]
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_upload(state, str(f), "scope_allowed")
        assert "Uploaded" in result
        mock_upload.assert_called_once()

    @patch("unique_sdk.Folder.create_paths")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_mkdir_blocked_by_metadata_filter(
        self, mock_path: MagicMock, mock_create: MagicMock
    ) -> None:
        """A per-message filter must gate folder creation, not just static
        scopeIds — mkdir under an out-of-scope cwd is denied (UN-21780).
        """
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A", "scope_other": "/Other"}
        )
        state = _state("/Other", "scope_other")
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_mkdir(state, "Q2")
        assert "permission denied" in result
        mock_create.assert_not_called()

    @patch("unique_sdk.Folder.create_paths")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_mkdir_allowed_by_metadata_filter(
        self, mock_path: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A"}
        )
        mock_create.return_value = {"createdFolders": [{"id": "scope_new"}]}
        state = _state("/Funds/Fund A", "scope_allowed")
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_mkdir(state, "Q2")
        assert "Created" in result
        mock_create.assert_called_once()

    @patch("unique_sdk.Folder.create_paths")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_mkdir_in_filter_not_blocked_by_static_scope(
        self, mock_path: MagicMock, mock_create: MagicMock
    ) -> None:
        """An active per-message filter replaces the static scopeIds, so an
        in-filter destination outside the static scope must not be over-denied
        by the static-scope check. See UN-21780.
        """
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A"}
        )
        mock_create.return_value = {"createdFolders": [{"id": "scope_new"}]}
        state = _state("/Funds/Fund A", "scope_allowed")
        # Static scope covers a different subtree; the filter is authoritative.
        state.workspace_scope_ids = ["scope_admin"]
        state._workspace_scope_paths = ["/Admin"]
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_mkdir(state, "Q2")
        assert "Created" in result
        mock_create.assert_called_once()

    @patch("unique_sdk.Folder.create_paths")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_mkdir_dotdot_escapes_metadata_filter_blocked(
        self, mock_path: MagicMock, mock_create: MagicMock
    ) -> None:
        """Regression: `mkdir ../Other/X` from an in-scope cwd must be denied —
        the gate checks the normalized destination path, not just cwd's scope
        id. See UN-21780.
        """
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_fund_a": "/Funds/Fund A"}
        )
        state = _state("/Funds/Fund A", "scope_fund_a")
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_fund_a",
        }
        result = cmd_mkdir(state, "../Fund B/Secret")
        assert "permission denied" in result
        mock_create.assert_not_called()

    @patch("unique_sdk.Folder.delete")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_rmdir_blocked_by_metadata_filter(
        self, mock_path: MagicMock, mock_delete: MagicMock
    ) -> None:
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A", "scope_other": "/Other"}
        )
        state = _state("/", None)
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_rmdir(state, "scope_other", recursive=True)
        assert "permission denied" in result
        mock_delete.assert_not_called()

    @patch("unique_sdk.Folder.update")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_mvdir_blocked_by_metadata_filter(
        self, mock_path: MagicMock, mock_update: MagicMock
    ) -> None:
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A", "scope_other": "/Other"}
        )
        state = _state("/", None)
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_mvdir(state, "scope_other", "New Name")
        assert "permission denied" in result
        mock_update.assert_not_called()

    @patch("unique_sdk.Folder.delete")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_rmdir_in_filter_not_blocked_by_static_scope(
        self, mock_path: MagicMock, mock_delete: MagicMock
    ) -> None:
        """An active per-message filter replaces the static scopeIds, so an
        in-filter target outside the static scope must not be over-denied by
        the static-scope check. See UN-21780.
        """
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A"}
        )
        state = _state("/", None)
        state.workspace_scope_ids = ["scope_admin"]
        state._workspace_scope_paths = ["/Admin"]
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_rmdir(state, "scope_allowed", recursive=True)
        assert "permission denied" not in result
        mock_delete.assert_called_once()

    @patch("unique_sdk.Folder.update")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_mvdir_in_filter_not_blocked_by_static_scope(
        self, mock_path: MagicMock, mock_update: MagicMock
    ) -> None:
        mock_path.side_effect = _folder_path_side_effect(
            {"scope_allowed": "/Funds/Fund A"}
        )
        mock_update.return_value = {"id": "scope_allowed", "name": "New Name"}
        state = _state("/", None)
        state.workspace_scope_ids = ["scope_admin"]
        state._workspace_scope_paths = ["/Admin"]
        state.workspace_metadata_filter = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "scope_allowed",
        }
        result = cmd_mvdir(state, "scope_allowed", "New Name")
        assert "permission denied" not in result
        mock_update.assert_called_once()

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.cli.commands.files.upload_file")
    @patch("unique_sdk.cli.commands.files.mimetypes.guess_type")
    def test_upload_xlsx_uses_supported_mime_type_mapping(
        self,
        mock_guess_type: MagicMock,
        mock_upload: MagicMock,
        mock_path: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"content")
        mock_result = MagicMock()
        mock_result.id = "cont_new"
        mock_upload.return_value = mock_result
        mock_path.return_value = {"folderPath": "/Reports"}
        mock_guess_type.return_value = (None, None)

        result = cmd_upload(_state("/Reports", "scope_r"), str(f))

        assert "Uploaded" in result
        assert mock_upload.call_args.kwargs["mime_type"] == (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        mock_guess_type.assert_not_called()

    @patch("unique_sdk.Content.versions")
    @patch("unique_sdk.Content.get_infos")
    def test_versions_by_name(
        self,
        mock_infos: MagicMock,
        mock_versions: MagicMock,
    ) -> None:
        mock_infos.return_value = {"contentInfos": [_content_info()]}
        mock_versions.return_value = {
            "data": [
                {
                    "id": "cver_1",
                    "versionNumber": 1,
                    "archivedAt": "2026-06-06T12:00:00Z",
                    "reason": "REPLACED",
                    "title": "report.pdf",
                }
            ]
        }
        result = cmd_versions(_state("/R", "scope_r"), "report.pdf", take=10)
        assert "Versions for report.pdf" in result
        assert "cver_1" in result
        assert mock_versions.call_args.kwargs["contentId"] == "cont_123"
        assert mock_versions.call_args.kwargs["take"] == 10

    @patch("unique_sdk.Content.versions")
    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_info")
    def test_versions_by_path(
        self,
        mock_folder: MagicMock,
        mock_infos: MagicMock,
        mock_versions: MagicMock,
    ) -> None:
        mock_folder.return_value = {"id": "scope_q1"}
        mock_infos.return_value = {"contentInfos": [_content_info()]}
        mock_versions.return_value = {"data": []}
        result = cmd_versions(_state("/Reports", "scope_r"), "/Reports/Q1/report.pdf")
        assert "Versions for report.pdf" in result
        assert mock_versions.call_args.kwargs["contentId"] == "cont_123"

    @patch("unique_sdk.Folder.get_info")
    def test_versions_path_outside_workspace_blocked(
        self,
        mock_folder: MagicMock,
    ) -> None:
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_versions(state, "/Outside/report.pdf")
        assert "permission denied" in result
        mock_folder.assert_not_called()

    @patch("unique_sdk.Content.get_info")
    def test_versions_content_id_outside_workspace_blocked(
        self,
        mock_info: MagicMock,
    ) -> None:
        mock_info.return_value = {"contentInfo": [{"ownerId": "scope_other"}]}
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_versions(state, "cont_outside")
        assert "permission denied" in result

    @patch("unique_sdk.Content.restore_version")
    def test_restore_version(self, mock_restore: MagicMock) -> None:
        mock_restore.return_value = _content_info(title="report.pdf")
        result = cmd_restore_version(_state(), "cver_1")
        assert "Restored" in result
        assert "cver_1" in result
        assert mock_restore.call_args.kwargs["contentVersionId"] == "cver_1"

    @patch("unique_sdk.Content.restore_version")
    def test_restore_version_workspace_restricted_inside_allowed(
        self,
        mock_restore: MagicMock,
    ) -> None:
        mock_restore.return_value = _content_info(title="report.pdf")
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_restore_version(state, "cver_1")
        assert "Restored" in result
        assert mock_restore.call_args.kwargs["contentVersionId"] == "cver_1"

    @patch("unique_sdk.Content.restore_version")
    def test_restore_version_workspace_restricted_outside_blocked(
        self,
        mock_restore: MagicMock,
    ) -> None:
        state = _state("/Outside", "scope_other")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_restore_version(state, "cver_1")
        assert "permission denied" in result
        mock_restore.assert_not_called()

    @patch("unique_sdk.Content.restore_version")
    def test_restore_version_blocked_by_metadata_filter(
        self,
        mock_restore: MagicMock,
    ) -> None:
        """A per-message filter can't be verified before the restore mutates,
        so restore-version is denied while one is active (UN-21780).
        """
        state = _state()
        state.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_x"],
        }
        result = cmd_restore_version(state, "cver_1")
        assert "permission denied" in result
        mock_restore.assert_not_called()

    @patch("unique_sdk.Content.restore_version")
    def test_restore_version_filter_denial_precedes_static_scope(
        self,
        mock_restore: MagicMock,
    ) -> None:
        """When a per-message filter is active it replaces the static scope for
        the turn, so an out-of-static-scope cwd must still surface the
        filter-specific 'cannot verify the target' denial (with the task-scope
        hint), not the hint-less static denial. See UN-21780.
        """
        state = _state("/Outside", "scope_other")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        state.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_x"],
        }
        result = cmd_restore_version(state, "cver_1")
        assert "cannot verify the target" in result
        assert "outside workspace scope" not in result
        mock_restore.assert_not_called()

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

    @patch("unique_sdk.Content.get_info")
    def test_download_content_id_outside_workspace_blocked(
        self,
        mock_info: MagicMock,
    ) -> None:
        mock_info.return_value = {"contentInfo": [{"ownerId": "scope_other"}]}
        state = _state("/Workspace", "scope_ws")
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        result = cmd_download(state, "cont_outside")
        assert "permission denied" in result

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

    @patch("unique_sdk.cli.commands.files.shutil.move")
    @patch("unique_sdk.cli.commands.files.download_content")
    @patch("unique_sdk.cli.commands.files._resolve_content_id")
    def test_download_sanitizes_path_traversal(
        self,
        mock_resolve: MagicMock,
        mock_dl: MagicMock,
        mock_move: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        mock_resolve.return_value = ("cont_123", "../../.bashrc")
        mock_dl.return_value = tmp_path / "downloaded"
        cmd_download(_state("/R", "scope_r"), "cont_123", str(tmp_path))
        move_dest = mock_move.call_args[0][1]
        assert ".." not in move_dest

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

    @patch("unique_sdk.Search.create")
    def test_cmd_search_uses_workspace_scope_ids(self, mock: MagicMock) -> None:
        mock.return_value = []
        state = _state()
        state.workspace_scope_ids = ["scope_ws1", "scope_ws2"]
        result = cmd_search(state, "query")
        assert "No results found" in result
        call_kwargs = mock.call_args[1]
        assert call_kwargs["scopeIds"] == ["scope_ws1", "scope_ws2"]

    @patch("unique_sdk.Search.create")
    def test_cmd_search_explicit_folder_overrides_workspace(
        self, mock: MagicMock
    ) -> None:
        mock.return_value = []
        with patch("unique_sdk.Folder.get_info") as mock_info:
            mock_info.return_value = {"id": "scope_explicit"}
            state = _state()
            state.workspace_scope_ids = ["scope_ws"]
            result = cmd_search(state, "query", folder="/Reports")
        assert "No results found" in result
        call_kwargs = mock.call_args[1]
        assert call_kwargs["scopeIds"] == ["scope_explicit"]


class TestReadPayload:
    def test_inline_payload(self) -> None:
        result = _read_payload('{"name": "tool"}', None, False)
        assert result == '{"name": "tool"}'

    def test_no_source_raises(self) -> None:
        with pytest.raises(ValueError, match="No payload provided"):
            _read_payload(None, None, False)

    def test_multiple_sources_raises(self) -> None:
        with pytest.raises(ValueError, match="Ambiguous input"):
            _read_payload('{"name": "tool"}', "file.json", False)

    def test_file_source(self, tmp_path: Any) -> None:
        f = tmp_path / "payload.json"
        f.write_text('{"name": "tool"}')
        result = _read_payload(None, str(f), False)
        assert result == '{"name": "tool"}'

    def test_stdin_source(self) -> None:
        with patch("unique_sdk.cli.commands.mcp.sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = '{"name": "tool"}'
            result = _read_payload(None, None, True)
            assert result == '{"name": "tool"}'


class TestParseAndValidate:
    def test_valid_payload(self) -> None:
        name, args = _parse_and_validate('{"name": "search", "arguments": {"q": "x"}}')
        assert name == "search"
        assert args == {"q": "x"}

    def test_missing_arguments_defaults_empty(self) -> None:
        name, args = _parse_and_validate('{"name": "tool"}')
        assert name == "tool"
        assert args == {}

    def test_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            _parse_and_validate("not json")

    def test_not_object(self) -> None:
        with pytest.raises(ValueError, match="must be a JSON object"):
            _parse_and_validate("[1, 2, 3]")

    def test_missing_name(self) -> None:
        with pytest.raises(ValueError, match='Missing required field "name"'):
            _parse_and_validate('{"arguments": {}}')

    def test_arguments_not_object(self) -> None:
        with pytest.raises(ValueError, match='"arguments" must be a JSON object'):
            _parse_and_validate('{"name": "tool", "arguments": "bad"}')


def _mcp_response(
    tool_name: str = "tool",
    is_error: bool = False,
    server_id: str = "srv_1",
    content: list[dict[str, Any]] | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.name = tool_name
    resp.isError = is_error
    resp.mcpServerId = server_id
    resp.content = content if content is not None else []
    return resp


class TestCmdMcp:
    @patch("unique_sdk.MCP.call_tool")
    def test_success(self, mock: MagicMock) -> None:
        mock.return_value = _mcp_response(
            tool_name="search",
            server_id="mcp_srv_1",
            content=[{"type": "text", "text": "result"}],
        )
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            payload='{"name": "search", "arguments": {"q": "test"}}',
        )
        assert "MCP tool call: search" in result
        assert "mcp_srv_1" in result
        assert "[text] result" in result
        mock.assert_called_once_with(
            user_id="u1",
            company_id="c1",
            name="search",
            chatId="chat_1",
            messageId="msg_1",
            arguments={"q": "test"},
        )

    def test_invalid_json_error(self) -> None:
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            payload="not json",
        )
        assert "mcp:" in result
        assert "Invalid JSON" in result

    def test_missing_name_error(self) -> None:
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            payload='{"arguments": {}}',
        )
        assert "mcp:" in result
        assert "name" in result

    def test_no_payload_error(self) -> None:
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
        )
        assert "mcp:" in result
        assert "No payload" in result

    @patch("unique_sdk.MCP.call_tool")
    def test_api_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("API failed")
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            payload='{"name": "tool", "arguments": {}}',
        )
        assert "mcp:" in result

    @patch("unique_sdk.MCP.call_tool")
    def test_file_input(self, mock: MagicMock, tmp_path: Any) -> None:
        f = tmp_path / "payload.json"
        f.write_text('{"name": "tool", "arguments": {"k": "v"}}')
        mock.return_value = _mcp_response(content=[{"type": "text", "text": "ok"}])
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            file=str(f),
        )
        assert "MCP tool call: tool" in result
        mock.assert_called_once()

    def test_file_not_found_error(self) -> None:
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            file="/nonexistent/payload.json",
        )
        assert "mcp:" in result

    @patch("unique_sdk.MCP.call_tool")
    def test_lean_response_falls_back_to_payload_tool_name(
        self, mock: MagicMock
    ) -> None:
        """Spec-compliant response with only ``content`` must not crash and must
        show the caller-supplied tool name in the header."""

        class _LeanResponse:
            """Mimics ``UniqueObject``: missing keys raise ``AttributeError``."""

            def __init__(self) -> None:
                self.content = [{"type": "text", "text": "hello"}]

        mock.return_value = _LeanResponse()
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            payload='{"name": "search_emails", "arguments": {}}',
        )
        assert "MCP tool call: search_emails" in result
        assert "Server: <unknown-server>" in result
        assert "[text] hello" in result
        assert "Traceback" not in result

    @patch("unique_sdk.cli.commands.mcp.format_mcp_response")
    @patch("unique_sdk.MCP.call_tool")
    def test_formatter_error_falls_back_to_raw_payload(
        self, call_mock: MagicMock, fmt_mock: MagicMock
    ) -> None:
        """A bug in the formatter must not hide a successful API response."""
        call_mock.return_value = _mcp_response(
            tool_name="tool", content=[{"type": "text", "text": "payload"}]
        )
        fmt_mock.side_effect = RuntimeError("boom")
        result = cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            payload='{"name": "tool", "arguments": {}}',
        )
        assert "formatter error" in result
        assert "raw response:" in result

    @patch("unique_sdk.cli.commands.mcp.format_mcp_response")
    @patch("unique_sdk.MCP.call_tool")
    def test_cmd_mcp_forwards_tool_name_to_formatter(
        self, call_mock: MagicMock, fmt_mock: MagicMock
    ) -> None:
        """``cmd_mcp`` must thread the parsed payload name into the formatter."""
        call_mock.return_value = _mcp_response(content=[])
        fmt_mock.return_value = "ok"
        cmd_mcp(
            _state(),
            chat_id="chat_1",
            message_id="msg_1",
            payload='{"name": "search_emails", "arguments": {}}',
        )
        fmt_mock.assert_called_once()
        _, kwargs = fmt_mock.call_args
        assert kwargs.get("tool_name") == "search_emails"


# --- Scheduled Tasks ---


def _scheduled_task_obj(
    task_id: str = "task_abc",
    cron: str = "0 9 * * 1-5",
    assistant_id: str = "ast_123",
    assistant_name: str = "Report Bot",
    prompt: str = "Generate report",
    enabled: bool = True,
) -> MagicMock:
    task = MagicMock()
    task.id = task_id
    task.object = "scheduled_task"
    task.cronExpression = cron
    task.assistantId = assistant_id
    task.assistantName = assistant_name
    task.chatId = None
    task.prompt = prompt
    task.enabled = enabled
    task.lastRunAt = None
    task.createdAt = "2026-04-01T00:00:00Z"
    task.updatedAt = "2026-04-01T00:00:00Z"
    return task


class TestScheduledTasks:
    @patch("unique_sdk.ScheduledTask.list")
    def test_list_empty(self, mock: MagicMock) -> None:
        mock.return_value = []
        result = cmd_schedule_list(_state())
        assert "No scheduled tasks found" in result

    @patch("unique_sdk.ScheduledTask.list")
    def test_list_with_tasks(self, mock: MagicMock) -> None:
        mock.return_value = [_scheduled_task_obj()]
        result = cmd_schedule_list(_state())
        assert "1 scheduled task(s)" in result
        assert "task_abc" in result
        assert "0 9 * * 1-5" in result

    @patch("unique_sdk.ScheduledTask.list")
    def test_list_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("fail")
        result = cmd_schedule_list(_state())
        assert "schedule:" in result

    @patch("unique_sdk.ScheduledTask.retrieve")
    def test_get(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task_obj()
        result = cmd_schedule_get(_state(), "task_abc")
        assert "task_abc" in result
        assert "0 9 * * 1-5" in result
        assert "Report Bot" in result

    @patch("unique_sdk.ScheduledTask.retrieve")
    def test_get_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("not found")
        result = cmd_schedule_get(_state(), "task_xyz")
        assert "schedule:" in result

    @patch("unique_sdk.ScheduledTask.create")
    def test_create(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task_obj()
        result = cmd_schedule_create(
            _state(),
            cron="0 9 * * 1-5",
            assistant_id="ast_123",
            prompt="Generate report",
        )
        assert "Created scheduled task task_abc" in result
        mock.assert_called_once()

    @patch("unique_sdk.ScheduledTask.create")
    def test_create_with_chat_id(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task_obj()
        result = cmd_schedule_create(
            _state(),
            cron="0 9 * * 1-5",
            assistant_id="ast_123",
            prompt="Continue chat",
            chat_id="chat_456",
        )
        assert "Created" in result
        call_kwargs = mock.call_args[1]
        assert call_kwargs["chatId"] == "chat_456"

    @patch("unique_sdk.ScheduledTask.create")
    def test_create_disabled(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task_obj(enabled=False)
        result = cmd_schedule_create(
            _state(),
            cron="0 9 * * 1-5",
            assistant_id="ast_123",
            prompt="Report",
            enabled=False,
        )
        assert "Created" in result
        call_kwargs = mock.call_args[1]
        assert call_kwargs["enabled"] is False

    @patch("unique_sdk.ScheduledTask.create")
    def test_create_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("bad cron")
        result = cmd_schedule_create(
            _state(),
            cron="bad",
            assistant_id="ast_123",
            prompt="Report",
        )
        assert "schedule:" in result

    @patch("unique_sdk.ScheduledTask.modify")
    def test_update(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task_obj(enabled=False)
        result = cmd_schedule_update(_state(), "task_abc", enabled=False)
        assert "Updated scheduled task task_abc" in result

    @patch("unique_sdk.ScheduledTask.modify")
    def test_update_cron(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task_obj(cron="*/15 * * * *")
        result = cmd_schedule_update(_state(), "task_abc", cron="*/15 * * * *")
        assert "Updated" in result
        call_kwargs = mock.call_args[1]
        assert call_kwargs["cronExpression"] == "*/15 * * * *"

    def test_update_nothing(self) -> None:
        result = cmd_schedule_update(_state(), "task_abc")
        assert "nothing to update" in result

    @patch("unique_sdk.ScheduledTask.modify")
    def test_update_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("not found")
        result = cmd_schedule_update(_state(), "task_abc", enabled=True)
        assert "schedule:" in result

    @patch("unique_sdk.ScheduledTask.delete")
    def test_delete(self, mock: MagicMock) -> None:
        mock.return_value = {
            "id": "task_abc",
            "object": "scheduled_task",
            "deleted": True,
        }
        result = cmd_schedule_delete(_state(), "task_abc")
        assert "Deleted scheduled task task_abc" in result

    @patch("unique_sdk.ScheduledTask.delete")
    def test_delete_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("not found")
        result = cmd_schedule_delete(_state(), "task_xyz")
        assert "schedule:" in result
