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
            "ingestionConfig": {"uniqueIngestionMode": "INGESTION"},
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-03-01T10:00:00Z",
            "parentId": "scope_root",
            "externalId": None,
            "scopeAccess": [],
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

    @patch("unique_sdk.MCP.call_tool")
    def test_mcp(self, mock: MagicMock) -> None:
        resp = MagicMock()
        resp.name = "tool"
        resp.isError = False
        resp.mcpServerId = "srv_1"
        resp.content = [{"type": "text", "text": "result"}]
        mock.return_value = resp
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "mcp",
                "-c",
                "chat_1",
                "-m",
                "msg_1",
                '{"name": "tool", "arguments": {}}',
            ],
        )
        assert result.exit_code == 0
        assert "MCP tool call: tool" in result.output

    def test_mcp_missing_chat_id(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["mcp", "-m", "msg_1", '{"name": "tool"}'],
        )
        assert result.exit_code != 0

    def test_mcp_missing_message_id(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["mcp", "-c", "chat_1", '{"name": "tool"}'],
        )
        assert result.exit_code != 0

    @patch("unique_sdk.MCP.call_tool")
    def test_mcp_file_input(self, mock: MagicMock) -> None:
        resp = MagicMock()
        resp.name = "tool"
        resp.isError = False
        resp.mcpServerId = "srv_1"
        resp.content = [{"type": "text", "text": "ok"}]
        mock.return_value = resp
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("payload.json", "w") as f:
                f.write('{"name": "tool", "arguments": {}}')
            result = runner.invoke(
                main,
                ["mcp", "-c", "chat_1", "-m", "msg_1", "-f", "payload.json"],
            )
        assert result.exit_code == 0
        assert "MCP tool call: tool" in result.output

    @patch("unique_sdk.MCP.call_tool")
    def test_mcp_stdin_input(self, mock: MagicMock) -> None:
        resp = MagicMock()
        resp.name = "tool"
        resp.isError = False
        resp.mcpServerId = "srv_1"
        resp.content = [{"type": "text", "text": "ok"}]
        mock.return_value = resp
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["mcp", "-c", "chat_1", "-m", "msg_1", "--stdin"],
            input='{"name": "tool", "arguments": {}}',
        )
        assert result.exit_code == 0

    def test_mcp_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["mcp", "-c", "chat_1", "-m", "msg_1", "not json"],
        )
        assert result.exit_code == 0
        assert "mcp:" in result.output

    # -- Schedule commands --

    def test_schedule_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "--help"])
        assert result.exit_code == 0
        assert "Manage cron-based scheduled tasks" in result.output

    @patch("unique_sdk.ScheduledTask.list")
    def test_schedule_list(self, mock: MagicMock) -> None:
        mock.return_value = []
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "list"])
        assert result.exit_code == 0
        assert "No scheduled tasks found" in result.output

    @patch("unique_sdk.ScheduledTask.retrieve")
    def test_schedule_get(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_1"
        task.cronExpression = "0 9 * * 1-5"
        task.assistantId = "ast_1"
        task.assistantName = "Bot"
        task.chatId = None
        task.prompt = "Report"
        task.enabled = True
        task.lastRunAt = None
        task.createdAt = "2026-04-01T00:00:00Z"
        task.updatedAt = "2026-04-01T00:00:00Z"
        mock.return_value = task
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "get", "task_1"])
        assert result.exit_code == 0
        assert "task_1" in result.output

    @patch("unique_sdk.ScheduledTask.create")
    def test_schedule_create(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_new"
        task.cronExpression = "0 9 * * 1-5"
        task.assistantId = "ast_1"
        task.assistantName = "Bot"
        task.chatId = None
        task.prompt = "Report"
        task.enabled = True
        task.lastRunAt = None
        task.createdAt = "2026-04-01T00:00:00Z"
        task.updatedAt = "2026-04-01T00:00:00Z"
        mock.return_value = task
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "schedule",
                "create",
                "--cron",
                "0 9 * * 1-5",
                "--assistant",
                "ast_1",
                "--prompt",
                "Report",
            ],
        )
        assert result.exit_code == 0
        assert "Created scheduled task task_new" in result.output

    @patch("unique_sdk.ScheduledTask.create")
    def test_schedule_create_disabled(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_new"
        task.cronExpression = "0 9 * * 1-5"
        task.assistantId = "ast_1"
        task.assistantName = "Bot"
        task.chatId = None
        task.prompt = "Report"
        task.enabled = False
        task.lastRunAt = None
        task.createdAt = "2026-04-01T00:00:00Z"
        task.updatedAt = "2026-04-01T00:00:00Z"
        mock.return_value = task
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "schedule",
                "create",
                "-c",
                "0 9 * * 1-5",
                "-a",
                "ast_1",
                "-p",
                "Report",
                "--disabled",
            ],
        )
        assert result.exit_code == 0
        assert "Created" in result.output

    @patch("unique_sdk.ScheduledTask.modify")
    def test_schedule_update(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_1"
        task.cronExpression = "0 9 * * 1-5"
        task.assistantId = "ast_1"
        task.assistantName = "Bot"
        task.chatId = None
        task.prompt = "Report"
        task.enabled = False
        task.lastRunAt = None
        task.createdAt = "2026-04-01T00:00:00Z"
        task.updatedAt = "2026-04-01T00:00:00Z"
        mock.return_value = task
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "update", "task_1", "--disable"])
        assert result.exit_code == 0
        assert "Updated" in result.output

    def test_schedule_update_enable_disable_conflict(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["schedule", "update", "task_1", "--enable", "--disable"]
        )
        assert result.exit_code == 0
        assert "cannot use --enable and --disable together" in result.output

    @patch("unique_sdk.ScheduledTask.delete")
    def test_schedule_delete(self, mock: MagicMock) -> None:
        mock.return_value = {
            "id": "task_1",
            "object": "scheduled_task",
            "deleted": True,
        }
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "delete", "task_1"])
        assert result.exit_code == 0
        assert "Deleted scheduled task task_1" in result.output
