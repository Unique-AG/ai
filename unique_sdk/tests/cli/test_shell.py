"""Tests for unique_sdk.cli.shell (interactive REPL)."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

from unique_sdk.cli.config import Config
from unique_sdk.cli.shell import UniqueShell
from unique_sdk.cli.state import ShellState


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


def _shell(path: str = "/", scope_id: str | None = None) -> UniqueShell:
    state = ShellState(_config())
    state._path = path
    state._scope_id = scope_id
    sh = UniqueShell(state)
    return sh


def _capture(shell: UniqueShell, command: str) -> str:
    """Run a command and capture its printed output."""
    buf = StringIO()
    shell._print = lambda text: buf.write(text + "\n")  # type: ignore[assignment]
    shell.onecmd(command)
    return buf.getvalue()


class TestShellBasics:
    def test_init_prompt(self) -> None:
        sh = _shell()
        assert sh.prompt == "/> "

    def test_emptyline(self) -> None:
        sh = _shell()
        assert sh.emptyline() is False

    def test_exit(self) -> None:
        sh = _shell()
        assert sh.do_exit("") is True

    def test_quit(self) -> None:
        sh = _shell()
        assert sh.do_quit("") is True

    def test_eof(self) -> None:
        sh = _shell()
        assert sh.do_EOF("") is True

    def test_default(self) -> None:
        out = _capture(_shell(), "bogus_cmd")
        assert "Unknown command: bogus_cmd" in out

    def test_help_overview(self) -> None:
        out = _capture(_shell(), "help")
        assert "Navigate the knowledge base" in out

    def test_help_specific(self, capsys) -> None:  # type: ignore[no-untyped-def]
        sh = _shell()
        sh.onecmd("help pwd")
        captured = capsys.readouterr()
        assert "Print the current working directory" in captured.out


class TestShellNavigation:
    def test_pwd(self) -> None:
        out = _capture(_shell("/Reports"), "pwd")
        assert "/Reports" in out

    @patch("unique_sdk.Folder.get_info")
    def test_cd(self, mock_get_info: MagicMock) -> None:
        mock_get_info.return_value = {"id": "scope_r"}
        sh = _shell()
        out = _capture(sh, "cd Reports")
        assert "/Reports" in out
        assert sh.prompt == "/Reports> "

    def test_cd_no_arg(self) -> None:
        sh = _shell("/Reports", "scope_r")
        out = _capture(sh, "cd")
        assert "/" in out

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    def test_ls(self, mock_folder: MagicMock, mock_content: MagicMock) -> None:
        mock_folder.return_value = {
            "folderInfos": [],
            "totalCount": 0,
        }
        mock_content.return_value = {
            "contentInfos": [],
            "totalCount": 0,
        }
        out = _capture(_shell(), "ls")
        assert "0 folder(s), 0 file(s)" in out

    @patch("unique_sdk.Content.get_infos")
    @patch("unique_sdk.Folder.get_infos")
    @patch("unique_sdk.Folder.get_info")
    def test_ls_with_path(
        self,
        mock_info: MagicMock,
        mock_infos: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_info.return_value = {"id": "scope_r"}
        mock_infos.return_value = {
            "folderInfos": [],
            "totalCount": 0,
        }
        mock_content.return_value = {
            "contentInfos": [],
            "totalCount": 0,
        }
        out = _capture(_shell(), "ls /Reports")
        assert "0 folder(s), 0 file(s)" in out


class TestShellFolderOps:
    @patch("unique_sdk.Folder.create_paths")
    def test_mkdir(self, mock: MagicMock) -> None:
        mock.return_value = {
            "createdFolders": [{"id": "scope_new"}],
        }
        out = _capture(_shell("/R", "scope_r"), "mkdir Q2")
        assert "Created" in out

    def test_mkdir_empty(self) -> None:
        out = _capture(_shell(), "mkdir")
        assert "Usage:" in out

    @patch("unique_sdk.Folder.delete")
    def test_rmdir(self, mock: MagicMock) -> None:
        out = _capture(_shell("/R", "scope_r"), "rmdir Q2")
        assert "Deleted" in out

    def test_rmdir_empty(self) -> None:
        out = _capture(_shell(), "rmdir")
        assert "Usage:" in out

    @patch("unique_sdk.Folder.delete")
    def test_rmdir_recursive(self, mock: MagicMock) -> None:
        out = _capture(_shell(), "rmdir scope_abc -r")
        assert "Deleted" in out
        mock.assert_called_once()
        call_kwargs = mock.call_args[1]
        assert call_kwargs["recursive"] is True

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
        out = _capture(_shell("/R", "scope_r"), "mvdir Q1 New")
        assert "Renamed" in out

    def test_mvdir_wrong_args(self) -> None:
        out = _capture(_shell(), "mvdir only_one")
        assert "Usage:" in out


class TestShellFileOps:
    def test_upload_empty(self) -> None:
        out = _capture(_shell(), "upload")
        assert "Usage:" in out

    def test_upload_nonexistent(self) -> None:
        out = _capture(_shell("/R", "scope_r"), "upload /nonexistent/f.pdf")
        assert "local file not found" in out

    @patch("unique_sdk.cli.commands.files.upload_file")
    @patch("unique_sdk.Folder.get_folder_path")
    def test_upload_with_dest(
        self,
        mock_path: MagicMock,
        mock_upload: MagicMock,
        tmp_path,  # type: ignore[no-untyped-def]
    ) -> None:
        f = tmp_path / "test.pdf"
        f.write_text("data")
        mock_result = MagicMock()
        mock_result.id = "cont_new"
        mock_upload.return_value = mock_result
        mock_path.return_value = {"folderPath": "/R"}
        out = _capture(_shell("/R", "scope_r"), f"upload {f} new.pdf")
        assert "Uploaded" in out

    def test_download_empty(self) -> None:
        out = _capture(_shell(), "download")
        assert "Usage:" in out

    @patch("unique_sdk.cli.commands.files.shutil.move")
    @patch("unique_sdk.cli.commands.files.download_content")
    def test_download(self, mock_dl: MagicMock, mock_move: MagicMock) -> None:
        mock_dl.return_value = "/tmp/downloaded"
        out = _capture(_shell(), "download cont_abc")
        assert "Downloaded" in out

    @patch("unique_sdk.cli.commands.files.shutil.move")
    @patch("unique_sdk.cli.commands.files.download_content")
    def test_download_with_dest(
        self,
        mock_dl: MagicMock,
        mock_move: MagicMock,
    ) -> None:
        mock_dl.return_value = "/tmp/downloaded"
        out = _capture(_shell(), "download cont_abc /tmp/out")
        assert "Downloaded" in out

    def test_rm_empty(self) -> None:
        out = _capture(_shell(), "rm")
        assert "Usage:" in out

    @patch("unique_sdk.Content.delete")
    def test_rm(self, mock: MagicMock) -> None:
        out = _capture(_shell(), "rm cont_abc")
        assert "Deleted" in out

    def test_mv_wrong_args(self) -> None:
        out = _capture(_shell(), "mv only_one")
        assert "Usage:" in out

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
        out = _capture(_shell(), "mv cont_abc new.pdf")
        assert "Renamed" in out


class TestShellSearch:
    def test_search_empty(self) -> None:
        out = _capture(_shell(), "search")
        assert "Usage:" in out

    @patch("unique_sdk.Search.create")
    def test_search_basic(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(_shell(), "search query")
        assert "No results found" in out

    @patch("unique_sdk.Search.create")
    def test_search_with_long_folder(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(_shell(), "search query --folder scope_abc")
        assert "No results found" in out

    @patch("unique_sdk.Search.create")
    def test_search_with_short_folder(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(_shell(), "search query -f scope_abc")
        assert "No results found" in out

    @patch("unique_sdk.Search.create")
    def test_search_with_metadata(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(_shell(), "search query --metadata dept=Legal")
        assert "No results found" in out

    @patch("unique_sdk.Search.create")
    def test_search_with_short_metadata(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(_shell(), "search query -m dept=Legal")
        assert "No results found" in out

    @patch("unique_sdk.Search.create")
    def test_search_with_limit(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(_shell(), "search query --limit 10")
        assert "No results found" in out

    @patch("unique_sdk.Search.create")
    def test_search_with_short_limit(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(_shell(), "search query -l 10")
        assert "No results found" in out

    def test_search_invalid_metadata(self) -> None:
        out = _capture(_shell(), "search query --metadata badformat")
        assert "Invalid metadata" in out

    def test_search_invalid_limit(self) -> None:
        out = _capture(_shell(), "search query --limit notanumber")
        assert "Invalid limit" in out

    @patch("unique_sdk.Search.create")
    def test_search_all_options(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(
            _shell(),
            "search revenue growth -f scope_abc -m dept=Legal -l 50",
        )
        assert "No results found" in out

    def test_search_only_flags_no_query(self) -> None:
        out = _capture(_shell(), "search --folder scope_abc")
        assert "Usage:" in out


def _mcp_response() -> MagicMock:
    resp = MagicMock()
    resp.name = "tool"
    resp.isError = False
    resp.mcpServerId = "srv_1"
    resp.content = [{"type": "text", "text": "ok"}]
    return resp


class TestShellMcp:
    def test_mcp_no_args(self) -> None:
        out = _capture(_shell(), "mcp")
        assert "Usage:" in out

    def test_mcp_missing_chat_id(self) -> None:
        out = _capture(_shell(), 'mcp -m msg_1 \'{"name": "tool"}\'')
        assert "--chat-id" in out

    def test_mcp_missing_message_id(self) -> None:
        out = _capture(_shell(), 'mcp -c chat_1 \'{"name": "tool"}\'')
        assert "--message-id" in out

    @patch("unique_sdk.MCP.call_tool")
    def test_mcp_inline_json(self, mock: MagicMock) -> None:
        mock.return_value = _mcp_response()
        out = _capture(
            _shell(),
            'mcp -c chat_1 -m msg_1 \'{"name": "tool", "arguments": {}}\'',
        )
        assert "MCP tool call: tool" in out
        mock.assert_called_once()

    @patch("unique_sdk.MCP.call_tool")
    def test_mcp_long_flags(self, mock: MagicMock) -> None:
        mock.return_value = _mcp_response()
        out = _capture(
            _shell(),
            'mcp --chat-id chat_1 --message-id msg_1 \'{"name": "tool"}\'',
        )
        assert "MCP tool call: tool" in out

    def test_mcp_invalid_json(self) -> None:
        out = _capture(_shell(), "mcp -c chat_1 -m msg_1 not_json")
        assert "mcp:" in out

    @patch("unique_sdk.MCP.call_tool")
    def test_mcp_file_flag(self, mock: MagicMock, tmp_path: MagicMock) -> None:
        f = tmp_path / "payload.json"
        f.write_text('{"name": "tool", "arguments": {}}')
        mock.return_value = _mcp_response()
        out = _capture(_shell(), f"mcp -c chat_1 -m msg_1 --file {f}")
        assert "MCP tool call: tool" in out


def _scheduled_task() -> MagicMock:
    task = MagicMock()
    task.id = "task_abc"
    task.cronExpression = "0 9 * * 1-5"
    task.assistantId = "ast_123"
    task.assistantName = "Bot"
    task.chatId = None
    task.prompt = "Generate report"
    task.enabled = True
    task.lastRunAt = None
    task.createdAt = "2026-04-01T00:00:00Z"
    task.updatedAt = "2026-04-01T00:00:00Z"
    return task


class TestShellSchedule:
    def test_schedule_no_args(self) -> None:
        out = _capture(_shell(), "schedule")
        assert "Usage:" in out

    def test_schedule_unknown_subcommand(self) -> None:
        out = _capture(_shell(), "schedule bogus")
        assert "Unknown subcommand" in out

    @patch("unique_sdk.ScheduledTask.list")
    def test_schedule_list(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = _capture(_shell(), "schedule list")
        assert "No scheduled tasks found" in out

    @patch("unique_sdk.ScheduledTask.retrieve")
    def test_schedule_get(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task()
        out = _capture(_shell(), "schedule get task_abc")
        assert "task_abc" in out

    def test_schedule_get_no_id(self) -> None:
        out = _capture(_shell(), "schedule get")
        assert "Usage:" in out

    @patch("unique_sdk.ScheduledTask.create")
    def test_schedule_create(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task()
        out = _capture(
            _shell(),
            'schedule create -c "0 9 * * 1-5" -a ast_123 -p "Generate report"',
        )
        assert "Created" in out

    def test_schedule_create_missing_required(self) -> None:
        out = _capture(_shell(), "schedule create -c '0 9 * * 1-5'")
        assert "Usage:" in out

    @patch("unique_sdk.ScheduledTask.create")
    def test_schedule_create_with_all_options(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task()
        out = _capture(
            _shell(),
            'schedule create -c "0 9 * * 1-5" -a ast_123 -p "Report" --chat-id chat_1 --disabled',
        )
        assert "Created" in out

    def test_schedule_create_unknown_option(self) -> None:
        out = _capture(
            _shell(),
            'schedule create -c "0 9 * * 1-5" -a ast_123 -p "Report" --bad',
        )
        assert "Unknown option" in out

    @patch("unique_sdk.ScheduledTask.modify")
    def test_schedule_update(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task()
        out = _capture(_shell(), "schedule update task_abc --disable")
        assert "Updated" in out

    def test_schedule_update_no_id(self) -> None:
        out = _capture(_shell(), "schedule update")
        assert "Usage:" in out

    @patch("unique_sdk.ScheduledTask.modify")
    def test_schedule_update_all_options(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task()
        out = _capture(
            _shell(),
            'schedule update task_abc -c "*/15 * * * *" -a ast_456 -p "New prompt" --enable',
        )
        assert "Updated" in out

    @patch("unique_sdk.ScheduledTask.modify")
    def test_schedule_update_clear_chat_id(self, mock: MagicMock) -> None:
        mock.return_value = _scheduled_task()
        out = _capture(_shell(), "schedule update task_abc --chat-id none")
        assert "Updated" in out

    def test_schedule_update_enable_disable_conflict(self) -> None:
        out = _capture(_shell(), "schedule update task_abc --enable --disable")
        assert "cannot use --enable and --disable together" in out

    def test_schedule_update_unknown_option(self) -> None:
        out = _capture(_shell(), "schedule update task_abc --bad")
        assert "Unknown option" in out

    @patch("unique_sdk.ScheduledTask.delete")
    def test_schedule_delete(self, mock: MagicMock) -> None:
        mock.return_value = {
            "id": "task_abc",
            "object": "scheduled_task",
            "deleted": True,
        }
        out = _capture(_shell(), "schedule delete task_abc")
        assert "Deleted" in out

    def test_schedule_delete_no_id(self) -> None:
        out = _capture(_shell(), "schedule delete")
        assert "Usage:" in out
