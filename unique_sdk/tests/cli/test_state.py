"""Tests for unique_sdk.cli.state."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

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


class TestShellState:
    def test_initial_state(self) -> None:
        s = ShellState(_config())
        assert s.cwd == "/"
        assert s.scope_id is None
        assert s.prompt == "/> "

    def test_cd_root(self) -> None:
        s = ShellState(_config())
        result = s.cd("/")
        assert result == "/"
        assert s.scope_id is None

    def test_cd_parent_at_root(self) -> None:
        s = ShellState(_config())
        result = s.cd("..")
        assert result == "/"

    @patch("unique_sdk.Folder.get_info")
    def test_cd_relative(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_reports"}
        s = ShellState(_config())
        result = s.cd("Reports")
        assert result == "/Reports"
        assert s.scope_id == "scope_reports"
        mock_get_info.assert_called_once_with(
            user_id="u1",
            company_id="c1",
            folderPath="/Reports",
        )

    @patch("unique_sdk.Folder.get_info")
    def test_cd_absolute(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_q1"}
        s = ShellState(_config())
        result = s.cd("/Company/Reports/Q1")
        assert result == "/Company/Reports/Q1"
        assert s.scope_id == "scope_q1"

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Folder.get_info")
    def test_cd_scope_id(self, mock_get_info, mock_get_path) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_abc"}
        mock_get_path.return_value = {"folderPath": "/Company/Reports"}
        s = ShellState(_config())
        result = s.cd("scope_abc")
        assert result == "/Company/Reports"
        assert s.scope_id == "scope_abc"

    @patch("unique_sdk.Folder.get_info")
    def test_cd_parent(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_reports"}
        s = ShellState(_config())
        s._path = "/Company/Reports/Q1"
        s._scope_id = "scope_q1"
        result = s.cd("..")
        assert result == "/Company/Reports"
        assert s.scope_id == "scope_reports"

    def test_cd_parent_to_root(self) -> None:
        s = ShellState(_config())
        s._path = "/Reports"
        s._scope_id = "scope_reports"
        result = s.cd("..")
        assert result == "/"
        assert s.scope_id is None

    def test_resolve_path_none(self) -> None:
        s = ShellState(_config())
        path, sid = s.resolve_path(None)
        assert path == "/"
        assert sid is None

    def test_resolve_path_root(self) -> None:
        s = ShellState(_config())
        path, sid = s.resolve_path("/")
        assert path == "/"
        assert sid is None

    @patch("unique_sdk.Folder.get_folder_path")
    def test_resolve_path_scope_id(self, mock_get_path) -> None:  # type: ignore[no-untyped-def]
        mock_get_path.return_value = {"folderPath": "/Reports"}
        s = ShellState(_config())
        path, sid = s.resolve_path("scope_abc")
        assert path == "/Reports"
        assert sid == "scope_abc"

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_path_absolute(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_r"}
        s = ShellState(_config())
        path, sid = s.resolve_path("/Reports")
        assert path == "/Reports"
        assert sid == "scope_r"

    @patch("unique_sdk.Folder.get_info")
    def test_resolve_path_relative(self, mock_get_info) -> None:  # type: ignore[no-untyped-def]
        mock_get_info.return_value = {"id": "scope_q1"}
        s = ShellState(_config())
        s._path = "/Reports"
        s._scope_id = "scope_r"
        path, sid = s.resolve_path("Q1")
        assert path == "/Reports/Q1"
        assert sid == "scope_q1"

    def test_prompt_updates(self) -> None:
        s = ShellState(_config())
        assert s.prompt == "/> "
        s._path = "/Reports"
        assert s.prompt == "/Reports> "


class TestWorkspaceScopes:
    def test_no_config_file_returns_empty(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
            s = ShellState(_config())
        assert s.workspace_scope_ids == []
        assert not s.workspace_restricted

    def test_loads_scope_ids_from_config(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        (tmp_path / ".unique-search.json").write_text(  # type: ignore[union-attr]
            json.dumps({"scopeIds": ["scope_abc", "scope_def"]})
        )
        with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
            s = ShellState(_config())
        assert s.workspace_scope_ids == ["scope_abc", "scope_def"]
        assert s.workspace_restricted

    def test_invalid_json_returns_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        (tmp_path / ".unique-search.json").write_text("not json")  # type: ignore[union-attr]
        with patch("unique_sdk.cli.state.Path.cwd", return_value=tmp_path):
            s = ShellState(_config())
        assert s.workspace_scope_ids == []

    def test_is_within_workspace_no_restriction(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = []
        assert s.is_within_workspace()

    def test_is_within_workspace_direct_scope_match(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = []
        s._scope_id = "scope_abc"
        assert s.is_within_workspace()

    def test_is_within_workspace_path_prefix_descendant(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = ["/Company/Reports"]
        s._path = "/Company/Reports/Q1"
        assert s.is_within_workspace()

    def test_is_within_workspace_exact_path(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = ["/Company/Reports"]
        s._path = "/Company/Reports"
        assert s.is_within_workspace()

    def test_is_within_workspace_blocked_at_root(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = ["/Company/Reports"]
        s._path = "/"
        s._scope_id = None
        assert not s.is_within_workspace()

    def test_is_within_workspace_blocked_wrong_path(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = ["/Company/Reports"]
        s._path = "/Company/Finance"
        assert not s.is_within_workspace()

    @patch("unique_sdk.Folder.get_folder_path")
    def test_resolve_workspace_scope_paths_cached(self, mock_path: patch) -> None:  # type: ignore[valid-type]
        mock_path.return_value = {"folderPath": "/Company/Reports"}
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_abc"]
        s._workspace_scope_paths = None
        paths1 = s._resolve_workspace_scope_paths()
        paths2 = s._resolve_workspace_scope_paths()
        assert paths1 == ["/Company/Reports"]
        assert paths2 == ["/Company/Reports"]
        mock_path.assert_called_once()


class TestFolderTargetWithinWorkspace:
    def test_no_restriction_always_allowed(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = []
        assert s.is_folder_target_within_workspace("scope_other")
        assert s.is_folder_target_within_workspace("/any/path")

    def test_scope_id_direct_match(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = []
        assert s.is_folder_target_within_workspace("scope_ws")

    @patch("unique_sdk.Folder.get_folder_path")
    def test_scope_id_descendant_allowed(self, mock_path: patch) -> None:  # type: ignore[valid-type]
        mock_path.return_value = {"folderPath": "/Workspace/Sub"}
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert s.is_folder_target_within_workspace("scope_sub")

    @patch("unique_sdk.Folder.get_folder_path")
    def test_scope_id_outside_workspace_blocked(self, mock_path: patch) -> None:  # type: ignore[valid-type]
        mock_path.return_value = {"folderPath": "/OtherTenant/Folder"}
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert not s.is_folder_target_within_workspace("scope_other")

    @patch("unique_sdk.Folder.get_folder_path")
    def test_scope_id_api_error_blocks(self, mock_path: patch) -> None:  # type: ignore[valid-type]
        mock_path.side_effect = Exception("network error")
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert not s.is_folder_target_within_workspace("scope_unknown")

    def test_absolute_path_within_workspace_allowed(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert s.is_folder_target_within_workspace("/Workspace/Sub/Deep")

    def test_absolute_path_outside_workspace_blocked(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        assert not s.is_folder_target_within_workspace("/OtherTenant/Folder")

    def test_relative_path_delegates_to_cwd_check(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        s._path = "/Workspace/Sub"
        assert s.is_folder_target_within_workspace("RelativeFolder")

    def test_relative_path_outside_cwd_blocked(self) -> None:
        s = ShellState(_config())
        s.workspace_scope_ids = ["scope_ws"]
        s._workspace_scope_paths = ["/Workspace"]
        s._path = "/"
        s._scope_id = None
        assert not s.is_folder_target_within_workspace("RelativeFolder")
