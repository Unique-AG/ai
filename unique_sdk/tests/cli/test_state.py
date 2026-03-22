"""Tests for unique_sdk.cli.state."""

from __future__ import annotations

from unittest.mock import patch

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
