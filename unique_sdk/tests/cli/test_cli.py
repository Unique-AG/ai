"""Tests for unique_sdk.cli.cli (Click entry point)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from unique_sdk.cli.cli import main


@patch.dict(
    os.environ,
    {
        "UNIQUE_API_KEY": "ukey_test",
        "UNIQUE_APP_ID": "app_test",
        "UNIQUE_USER_ID": "user_test",
        "UNIQUE_COMPANY_ID": "company_test",
    },
    clear=False,
)
class TestClickCLI:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Unique CLI" in result.output

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "unique-cli" in result.output

    def test_pwd(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["pwd"])
        assert result.exit_code == 0
        assert "/" in result.output

    @patch("unique_sdk.Folder.get_info")
    def test_cd(self, mock: MagicMock) -> None:
        mock.return_value = {"id": "scope_r"}
        runner = CliRunner()
        result = runner.invoke(main, ["cd", "Reports"])
        assert result.exit_code == 0

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    def test_ls(self, mock_f: MagicMock, mock_c: MagicMock) -> None:
        mock_f.return_value = {"folderInfos": [], "totalCount": 0}
        mock_c.return_value = {"contentInfos": [], "totalCount": 0}
        runner = CliRunner()
        result = runner.invoke(main, ["ls"])
        assert result.exit_code == 0

    @patch("unique_sdk.Folder.create_paths")
    def test_mkdir(self, mock: MagicMock) -> None:
        mock.return_value = {"createdFolders": [{"id": "scope_new"}]}
        runner = CliRunner()
        result = runner.invoke(main, ["mkdir", "Test"])
        assert result.exit_code == 0
        assert "Created" in result.output

    @patch("unique_sdk.Folder.delete")
    def test_rmdir(self, mock: MagicMock) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["rmdir", "scope_abc"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    @patch("unique_sdk.Folder.update")
    def test_mvdir(self, mock: MagicMock) -> None:
        mock.return_value = {
            "id": "scope_abc",
            "name": "New",
            "ingestionConfig": {},
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-03-01T10:00:00Z",
            "parentId": "scope_root",
        }
        runner = CliRunner()
        result = runner.invoke(main, ["mvdir", "scope_abc", "New"])
        assert result.exit_code == 0
        assert "Renamed" in result.output

    @patch("unique_sdk.Content.delete")
    def test_rm(self, mock: MagicMock) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["rm", "cont_abc"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    @patch("unique_sdk.Content.update")
    def test_mv(self, mock: MagicMock) -> None:
        mock.return_value = {
            "id": "cont_abc",
            "key": "new.pdf",
            "url": None,
            "title": "new.pdf",
            "metadata": None,
            "mimeType": "application/pdf",
            "description": None,
            "byteSize": 1024,
            "ownerId": "user_1",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-03-01T10:00:00Z",
        }
        runner = CliRunner()
        result = runner.invoke(main, ["mv", "cont_abc", "new.pdf"])
        assert result.exit_code == 0
        assert "Renamed" in result.output

    @patch("unique_sdk.Search.create")
    def test_search(self, mock: MagicMock) -> None:
        mock.return_value = []
        runner = CliRunner()
        result = runner.invoke(main, ["search", "query"])
        assert result.exit_code == 0
        assert "No results found" in result.output

    @patch("unique_sdk.Search.create")
    def test_search_with_options(self, mock: MagicMock) -> None:
        mock.return_value = []
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["search", "query", "-f", "scope_abc", "-m", "dept=Legal", "-l", "50"],
        )
        assert result.exit_code == 0

    def test_search_bad_metadata(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["search", "query", "-m", "badformat"])
        assert result.exit_code == 0
        assert "Invalid metadata" in result.output

    def test_upload_nonexistent(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["upload", "/nonexistent/file.pdf"])
        assert result.exit_code == 0
        assert "local file not found" in result.output

    @patch("unique_sdk.cli.commands.files.shutil.move")
    @patch("unique_sdk.cli.commands.files.download_content")
    def test_download(self, mock_dl: MagicMock, mock_move: MagicMock) -> None:
        mock_dl.return_value = "/tmp/downloaded"
        runner = CliRunner()
        result = runner.invoke(main, ["download", "cont_abc"])
        assert result.exit_code == 0
