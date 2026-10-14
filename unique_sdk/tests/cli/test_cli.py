"""Tests for unique_sdk.cli.cli (Click entry point)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest
from click.testing import CliRunner

import unique_sdk
from unique_sdk._error import PermissionError as SdkPermissionError
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

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Folder.get_info")
    def test_cd(self, mock: MagicMock, mock_path: MagicMock) -> None:
        mock.return_value = {"id": "scope_r"}
        mock_path.return_value = {"folderPath": "/Reports"}
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

    @patch("unique_sdk.Folder.get_folder_path")
    @patch("unique_sdk.Folder.create_paths")
    def test_mkdir(self, mock: MagicMock, mock_path: MagicMock) -> None:
        mock.return_value = {"createdFolders": [{"id": "scope_new"}]}
        mock_path.return_value = {"folderPath": "/Test"}
        runner = CliRunner()
        result = runner.invoke(main, ["mkdir", "Test"])
        assert result.exit_code == 0
        assert "Created" in result.output

    @patch("unique_sdk.Folder.create_paths")
    def test_mkdir_error_exits_nonzero(self, mock: MagicMock) -> None:
        """A failed mkdir exits with code 1."""
        mock.side_effect = ValueError("Invalid request parameters")
        runner = CliRunner()
        result = runner.invoke(main, ["mkdir", "/demo/x"])
        assert result.exit_code == 1
        assert "mkdir:" in result.output

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

    @patch("unique_sdk.Search.create")
    def test_search_api_error_exits_nonzero(self, mock: MagicMock) -> None:
        """Bugbot regression: ``search:``-prefixed error strings must map
        to a non-zero exit code so shells / scripts can detect failures —
        mirroring the existing ``web-search`` behaviour.
        """
        from unique_sdk import APIError

        mock.side_effect = APIError("boom")
        runner = CliRunner()
        result = runner.invoke(main, ["search", "query"])
        assert result.exit_code == 1
        assert "search:" in result.output

    @patch("unique_sdk.cli.cli.cmd_ls")
    def test_ls_permission_denied_exits_nonzero(self, mock_ls: MagicMock) -> None:
        """Bugbot regression: an out-of-scope ls denial must exit non-zero so
        agent ``&&`` chains fail cleanly, like read/cite/download (UN-21780).
        """
        mock_ls.return_value = (
            "ls: permission denied: target is outside your task scope "
            "(folders: /Funds/Fund A)."
        )
        runner = CliRunner()
        result = runner.invoke(main, ["ls", "/Other"])
        assert result.exit_code == 1
        assert "permission denied" in result.output

    @patch("unique_sdk.cli.cli.cmd_ls")
    def test_ls_ok_exits_zero(self, mock_ls: MagicMock) -> None:
        mock_ls.return_value = "(empty)\n0 folder(s), 0 file(s)"
        runner = CliRunner()
        result = runner.invoke(main, ["ls"])
        assert result.exit_code == 0

    @patch("unique_sdk.cli.cli.cmd_versions")
    def test_versions_permission_denied_exits_nonzero(
        self, mock_versions: MagicMock
    ) -> None:
        """Bugbot regression: an out-of-scope versions denial must exit
        non-zero so agent ``&&`` chains fail cleanly (UN-21780).
        """
        mock_versions.return_value = (
            "versions: permission denied: cont_x is outside your task scope "
            "(folders: /Funds/Fund A)."
        )
        runner = CliRunner()
        result = runner.invoke(main, ["versions", "cont_x"])
        assert result.exit_code == 1
        assert "permission denied" in result.output

    @patch("unique_sdk.cli.cli.cmd_versions")
    def test_versions_ok_exits_zero(self, mock_versions: MagicMock) -> None:
        mock_versions.return_value = "No versions found."
        runner = CliRunner()
        result = runner.invoke(main, ["versions", "cont_x"])
        assert result.exit_code == 0

    @patch("unique_sdk.cli.cli.cmd_read")
    def test_read(self, mock_read: MagicMock) -> None:
        mock_read.return_value = "Content: doc (cont_abc) — 1 chunk(s)\n\ntext"
        runner = CliRunner()
        result = runner.invoke(main, ["read", "cont_abc"])
        assert result.exit_code == 0
        mock_read.assert_called_once_with(
            ANY, "cont_abc", from_page=None, to_page=None, max_chars=None
        )

    @patch("unique_sdk.cli.cli.cmd_read")
    def test_read_single_page(self, mock_read: MagicMock) -> None:
        mock_read.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(main, ["read", "cont_abc", "--page", "12"])
        assert result.exit_code == 0
        _, kwargs = mock_read.call_args
        assert kwargs["from_page"] == 12
        assert kwargs["to_page"] == 12

    @patch("unique_sdk.cli.cli.cmd_read")
    def test_read_range_and_max_chars(self, mock_read: MagicMock) -> None:
        mock_read.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "read",
                "cont_abc",
                "--from-page",
                "5",
                "--to-page",
                "9",
                "--max-chars",
                "100",
            ],
        )
        assert result.exit_code == 0
        _, kwargs = mock_read.call_args
        assert kwargs["from_page"] == 5
        assert kwargs["to_page"] == 9
        assert kwargs["max_chars"] == 100

    def test_read_page_conflict_exits_nonzero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["read", "cont_abc", "--page", "3", "--from-page", "1"]
        )
        assert result.exit_code == 1
        assert "use either" in result.output

    @patch("unique_sdk.cli.cli.cmd_read")
    def test_read_error_exits_nonzero(self, mock_read: MagicMock) -> None:
        mock_read.return_value = "read: no content found for ID: cont_abc"
        runner = CliRunner()
        result = runner.invoke(main, ["read", "cont_abc"])
        assert result.exit_code == 1
        assert "read:" in result.output

    def test_upload_nonexistent(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["upload", "/nonexistent/file.pdf"])
        assert result.exit_code == 1
        assert "local file not found" in result.output

    @pytest.mark.ai
    @patch("unique_sdk.cli.cli.cmd_upload")
    def test_upload_error_exits_nonzero(self, mock_upload: MagicMock) -> None:
        """Purpose: A refused upload exits non-zero even without a permission denial.
        Why this matters: Agents chained on exit code and reported uploads that did not happen.
        Setup summary: cmd_upload returns a folder-not-found line for a home path.
        """
        mock_upload.return_value = (
            "upload: folder not found: /home-user_1/second-brain/clients/X"
        )
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["upload", "./page.md", "/home-user_1/second-brain/clients/X/"],
        )
        assert result.exit_code == 1
        assert "folder not found: /home-user_1/second-brain/clients/X" in result.output

    @pytest.mark.ai
    @patch("unique_sdk.Folder.get_info")
    @patch("unique_sdk.Folder.create_paths")
    def test_mkdir_refused_exits_nonzero(
        self, mock_create: MagicMock, mock_info: MagicMock
    ) -> None:
        """Purpose: mkdir exits non-zero when the folder was not created.
        Why this matters: An empty create response used to print Created and exit 0.
        Setup summary: create_paths returns no folders and the path lookup misses.
        """
        mock_create.return_value = {"createdFolders": []}
        mock_info.side_effect = ValueError("not found")
        runner = CliRunner()
        result = runner.invoke(main, ["mkdir", "/home-user_1/second-brain/clients/X"])
        assert result.exit_code == 1
        assert "refused to create /home-user_1/second-brain/clients/X" in result.output

    @pytest.mark.ai
    @patch("unique_sdk.cli.cli.cmd_ls")
    def test_ls_unlistable_exits_nonzero(self, mock_ls: MagicMock) -> None:
        """Purpose: A not-listable folder exits non-zero.
        Why this matters: An empty listing was indistinguishable from a folder with no files.
        Setup summary: cmd_ls returns a cannot-list line that is not a permission denial.
        """
        mock_ls.return_value = (
            "ls: cannot list /home-user_1/second-brain/clients: "
            "resolved to /home-user_1 instead (not listable here)"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["ls", "/home-user_1/second-brain/clients"])
        assert result.exit_code == 1
        assert "not listable here" in result.output

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
        assert result.exit_code == 1
        assert "mcp:" in result.output

    @pytest.mark.ai
    def test_mcp__invalid_json__exits_1_with_unchanged_message(self) -> None:
        """Purpose: Invalid JSON is a failed connector call.

        Why this matters: An exit code of 0 makes the chat step look
        successful, so the agent treats a bad payload as a result.

        Setup summary: Invoke mcp with a non-JSON payload and assert exit 1
        plus the existing mcp: Invalid JSON line, with no traceback.
        """
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["mcp", "-c", "chat_1", "-m", "msg_1", "not json"],
        )
        assert result.exit_code == 1
        assert "mcp: Invalid JSON:" in result.output
        assert "Traceback" not in result.output

    @pytest.mark.ai
    def test_mcp__missing_name__exits_1_with_unchanged_message(self) -> None:
        """Purpose: A payload without name is a failed connector call.

        Why this matters: The command used to print the validation error and
        exit 0, which a chat step records as completed.

        Setup summary: Invoke mcp with a JSON object that has no name and
        assert exit 1 plus the existing missing-name line.
        """
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["mcp", "-c", "chat_1", "-m", "msg_1", '{"arguments": {}}'],
        )
        assert result.exit_code == 1
        assert 'mcp: Missing required field "name" in JSON payload.' in result.output
        assert "Traceback" not in result.output

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("error", "message"),
        [
            (
                unique_sdk.InvalidRequestError(
                    "MCP server not found. Unable to call tool.",
                    None,
                ),
                "MCP server not found. Unable to call tool.",
            ),
            (
                unique_sdk.AuthenticationError("unauthorized"),
                "unauthorized",
            ),
            (SdkPermissionError("forbidden"), "forbidden"),
            (
                unique_sdk.APIConnectionError("connection reset"),
                "connection reset",
            ),
        ],
        ids=[
            "invalid_request",
            "authentication",
            "permission",
            "connection",
        ],
    )
    @patch("unique_sdk.MCP.call_tool")
    def test_mcp__sdk_error__exits_1_without_traceback(
        self,
        mock_call: MagicMock,
        error: Exception,
        message: str,
    ) -> None:
        """Purpose: SDK errors print one mcp: line and exit 1.

        Why this matters: InvalidRequestError and its siblings are not
        subclasses of APIError, so they used to escape as a traceback.

        Setup summary: Raise each SDK error from the tool call and assert
        exit 1, the mcp: line, and no traceback.
        """
        mock_call.side_effect = error
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
        assert result.exit_code == 1
        assert f"mcp: {message}" in result.output
        assert "Traceback" not in result.output

    @pytest.mark.ai
    @patch("unique_sdk.MCP.call_tool")
    def test_mcp__api_error__exits_1_with_unchanged_message(
        self, mock_call: MagicMock
    ) -> None:
        """Purpose: APIError still prints mcp: and now exits 1.

        Why this matters: A 5xx used to be caught and printed, then the
        process exited 0, so the step looked completed.

        Setup summary: Raise APIError from the tool call and assert exit 1
        with the same mcp: line as before.
        """
        mock_call.side_effect = unique_sdk.APIError("API failed")
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
        assert result.exit_code == 1
        assert "mcp: API failed" in result.output
        assert "Traceback" not in result.output

    @pytest.mark.ai
    @patch("unique_sdk.MCP.call_tool")
    def test_mcp__is_error_result__exits_1_and_prints_formatted_result(
        self, mock_call: MagicMock
    ) -> None:
        """Purpose: A tool result with isError exits 1 and stays formatted.

        Why this matters: The connector already marked the result as an
        error, but the process exited 0, so the step looked completed.

        Setup summary: Return a tool result with isError set and assert
        exit 1, the (ERROR) tag, and the formatted text.
        """
        resp = MagicMock()
        resp.name = "tool"
        resp.isError = True
        resp.mcpServerId = "srv_1"
        resp.content = [{"type": "text", "text": "nope"}]
        mock_call.return_value = resp
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
        assert result.exit_code == 1
        assert "MCP tool call: tool (ERROR)" in result.output
        assert "[text] nope" in result.output

    @pytest.mark.ai
    @patch("unique_sdk.MCP.call_tool")
    def test_mcp__is_error_absent__exits_0(self, mock_call: MagicMock) -> None:
        """Purpose: A result that omits isError is still a success.

        Why this matters: Some backends only return content. Treating a
        missing flag as an error would fail successful connector calls.

        Setup summary: Return a response with content and no isError
        attribute and assert exit 0 without an (ERROR) tag.
        """

        class _ContentOnly:
            def __init__(self) -> None:
                self.name = "tool"
                self.mcpServerId = "srv_1"
                self.content = [{"type": "text", "text": "ok"}]

        mock_call.return_value = _ContentOnly()
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
        assert "(ERROR)" not in result.output

    @pytest.mark.ai
    @patch("unique_sdk.cli.commands.mcp.format_mcp_response")
    @patch("unique_sdk.MCP.call_tool")
    def test_mcp__formatter_error_on_success__exits_0(
        self, call_mock: MagicMock, fmt_mock: MagicMock
    ) -> None:
        """Purpose: A formatter bug on a successful result still exits 0.

        Why this matters: The tool call worked. Failing the step would hide
        a successful connector result behind an exit code.

        Setup summary: Return a successful tool result, raise from the
        formatter, and assert the fallback text with exit 0.
        """
        resp = MagicMock()
        resp.name = "tool"
        resp.isError = False
        resp.mcpServerId = "srv_1"
        resp.content = [{"type": "text", "text": "payload"}]
        call_mock.return_value = resp
        fmt_mock.side_effect = RuntimeError("boom")
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
        assert "mcp: formatter error (boom); raw response:" in result.output
        assert "Traceback" not in result.output

    @pytest.mark.ai
    @patch("unique_sdk.cli.commands.mcp.format_mcp_response")
    @patch("unique_sdk.MCP.call_tool")
    def test_mcp__formatter_error_on_is_error__exits_1(
        self, call_mock: MagicMock, fmt_mock: MagicMock
    ) -> None:
        """Purpose: A formatter bug does not hide an isError tool result.

        Why this matters: Error payloads are the ones most likely to break
        formatting. Exiting 0 would record the failed call as completed.

        Setup summary: Return a tool result with isError set, raise from the
        formatter, and assert the fallback text with exit 1.
        """
        resp = MagicMock()
        resp.name = "tool"
        resp.isError = True
        resp.mcpServerId = "srv_1"
        resp.content = [{"type": "text", "text": "nope"}]
        call_mock.return_value = resp
        fmt_mock.side_effect = RuntimeError("boom")
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
        assert result.exit_code == 1
        assert "mcp: formatter error (boom); raw response:" in result.output
        assert "Traceback" not in result.output

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

    @patch("unique_sdk.ScheduledTask.list")
    def test_schedule_list_error_exit_code(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("boom")
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "list"])
        assert result.exit_code == 1
        assert "schedule:" in result.output

    @patch("unique_sdk.ScheduledTask.retrieve")
    def test_schedule_get(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_1"
        task.name = None
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

    @patch("unique_sdk.ScheduledTask.retrieve")
    def test_schedule_get_error_exit_code(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("not found")
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "get", "task_xyz"])
        assert result.exit_code == 1
        assert "schedule:" in result.output

    @patch("unique_sdk.ScheduledTask.create")
    def test_schedule_create(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_new"
        task.name = None
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
    def test_schedule_create_error_exit_code(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("bad cron")
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "schedule",
                "create",
                "--cron",
                "bad",
                "--assistant",
                "ast_1",
                "--prompt",
                "Report",
            ],
        )
        assert result.exit_code == 1
        assert "schedule:" in result.output

    @patch("unique_sdk.ScheduledTask.create")
    def test_schedule_create_disabled(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_new"
        task.name = None
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

    @patch("unique_sdk.ScheduledTask.create")
    def test_schedule_create_with_name(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_new"
        task.name = "Daily sales report"
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
                "-c",
                "0 9 * * 1-5",
                "-a",
                "ast_1",
                "-p",
                "Report",
                "-n",
                "Daily sales report",
            ],
        )
        assert result.exit_code == 0
        assert mock.call_args[1]["name"] == "Daily sales report"

    @patch("unique_sdk.ScheduledTask.modify")
    def test_schedule_update_clear_name(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_1"
        task.name = None
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
        result = runner.invoke(main, ["schedule", "update", "task_1", "--name", "none"])
        assert result.exit_code == 0
        assert mock.call_args[1]["name"] is None

    @patch("unique_sdk.ScheduledTask.modify")
    def test_schedule_update(self, mock: MagicMock) -> None:
        task = MagicMock()
        task.id = "task_1"
        task.name = None
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

    @patch("unique_sdk.ScheduledTask.modify")
    def test_schedule_update_error_exit_code(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("not found")
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "update", "task_1", "--disable"])
        assert result.exit_code == 1
        assert "schedule:" in result.output

    def test_schedule_update_enable_disable_conflict(self) -> None:
        # Usage error, folded into the same ctx.exit(1) treatment as API errors.
        runner = CliRunner()
        result = runner.invoke(
            main, ["schedule", "update", "task_1", "--enable", "--disable"]
        )
        assert result.exit_code == 1
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

    @patch("unique_sdk.ScheduledTask.delete")
    def test_schedule_delete_error_exit_code(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("not found")
        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "delete", "task_xyz"])
        assert result.exit_code == 1
        assert "schedule:" in result.output

    # -- Out-of-scope denials must exit non-zero (UN-21780) --
    # Agents chain content access with shell `&&`; a denial that exited 0
    # would let the chain continue as if the read/cite/download succeeded.

    @patch("unique_sdk.cli.cli.cmd_cite_file")
    def test_cite_denial_exits_nonzero(self, mock_cite: MagicMock) -> None:
        mock_cite.return_value = (
            "cite: permission denied: cont_x is outside your task scope "
            "(folders: /Funds). Only cite documents within that scope or "
            "files attached to this chat."
        )
        runner = CliRunner()
        result = runner.invoke(
            main, ["cite", "cont_x", "--pages", "1", "--read-method", "text"]
        )
        assert result.exit_code == 1
        assert "permission denied" in result.output

    @patch("unique_sdk.cli.cli.cmd_cite_file")
    def test_cite_success_exits_zero(self, mock_cite: MagicMock) -> None:
        mock_cite.return_value = "[filesource1] -> cont_x page 1"
        runner = CliRunner()
        result = runner.invoke(
            main, ["cite", "cont_x", "--pages", "1", "--read-method", "text"]
        )
        assert result.exit_code == 0
        assert "[filesource1]" in result.output

    @patch("unique_sdk.cli.cli.cmd_download")
    def test_download_denial_exits_nonzero(self, mock_dl: MagicMock) -> None:
        mock_dl.return_value = (
            "download: permission denied: cont_x is outside your task scope "
            "(folders: /Funds). Use 'unique-cli search' or 'ls' instead."
        )
        runner = CliRunner()
        result = runner.invoke(main, ["download", "cont_x"])
        assert result.exit_code == 1
        assert "permission denied" in result.output

    @patch("unique_sdk.cli.cli.cmd_rm")
    def test_rm_denial_exits_nonzero(self, mock_rm: MagicMock) -> None:
        mock_rm.return_value = "rm: permission denied (outside workspace scope)"
        runner = CliRunner()
        result = runner.invoke(main, ["rm", "cont_x"])
        assert result.exit_code == 1
        assert "permission denied" in result.output

    @staticmethod
    def _write_chat_files_manifest() -> None:
        unique_dir = Path(".unique")
        unique_dir.mkdir(parents=True, exist_ok=True)
        (unique_dir / "chat-files.json").write_text(
            json.dumps({"report.pdf": "cont_x"}), encoding="utf-8"
        )

    def test_cite_with_canonical_method(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            self._write_chat_files_manifest()
            result = runner.invoke(
                main, ["cite", "report.pdf", "--pages", "3", "--read-method", "text"]
            )
            assert result.exit_code == 0
            assert "[filesource1] -> report.pdf page 3" in result.output

    def test_cite_accepts_tool_alias(self) -> None:
        # Bugbot #1: aliases like pymupdf must be accepted by the one-shot CLI
        # (previously rejected by click.Choice before normalization ran).
        runner = CliRunner()
        with runner.isolated_filesystem():
            self._write_chat_files_manifest()
            result = runner.invoke(
                main,
                ["cite", "report.pdf", "--pages", "3", "--read-method", "pymupdf"],
            )
            assert result.exit_code == 0
            assert "[filesource1] -> report.pdf page 3" in result.output

    def test_cite_rejects_unknown_method(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            self._write_chat_files_manifest()
            result = runner.invoke(
                main,
                ["cite", "report.pdf", "--pages", "3", "--read-method", "bogus"],
            )
            assert "--read-method is required and must be one of" in result.output

    def test_cite_requires_read_method(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["cite", "report.pdf", "--pages", "3"])
        assert result.exit_code != 0


class TestDenialDetectors:
    """Unit tests for the dispatcher's denial/error detectors (UN-21780)."""

    def test_cite_is_error_output(self) -> None:
        from unique_sdk.cli.commands.cite_file import is_error_output

        assert is_error_output("cite: permission denied: ...") is True
        assert is_error_output("cite: invalid --pages value") is True
        assert is_error_output("[filesource1] -> cont_x page 1") is False

    def test_files_is_permission_denied_output(self) -> None:
        from unique_sdk.cli.commands.files import (
            is_permission_denied_output,
        )

        assert (
            is_permission_denied_output(
                "rm: permission denied (outside workspace scope)"
            )
            is True
        )
        assert (
            is_permission_denied_output(
                "download: permission denied: cont_x is outside your task "
                "scope (folders: /Funds)."
            )
            is True
        )
        assert is_permission_denied_output("Downloaded: report.pdf -> ./x.pdf") is False
