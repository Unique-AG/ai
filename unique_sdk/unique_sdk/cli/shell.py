"""Interactive REPL shell using cmd.Cmd."""

from __future__ import annotations

import cmd
import shlex
import textwrap

from unique_sdk.cli import __version__
from unique_sdk.cli.commands.files import cmd_download, cmd_mv_file, cmd_rm, cmd_upload
from unique_sdk.cli.commands.folders import cmd_mkdir, cmd_mvdir, cmd_rmdir
from unique_sdk.cli.commands.mcp import cmd_mcp
from unique_sdk.cli.commands.navigation import cmd_cd, cmd_ls, cmd_pwd
from unique_sdk.cli.commands.scheduled_tasks import (
    cmd_schedule_create,
    cmd_schedule_delete,
    cmd_schedule_get,
    cmd_schedule_list,
    cmd_schedule_update,
)
from unique_sdk.cli.commands.search import cmd_search
from unique_sdk.cli.state import ShellState

OVERVIEW_HELP = textwrap.dedent("""\
    Unique CLI -- interactive file explorer for the Unique AI Platform.

    Navigate the knowledge base like a Linux filesystem. Folders are
    identified by name, path, or scope ID. Files are identified by
    name or content ID.

    Navigation:
      pwd                       Print current working directory
      cd <path|scope_id>        Change directory (supports .. and /)
      ls [path]                 List folders and files

    Folder operations:
      mkdir <name>              Create a new folder
      rmdir <target> [-r]       Delete a folder (use -r for recursive)
      mvdir <old> <new>         Rename a folder

    File operations:
      upload <local> [name]     Upload a local file
      download <name|id> [dest] Download a file to local machine
      rm <name|id>              Delete a file
      mv <old> <new>            Rename a file

    Search:
      search <query> [options]  Combined search (vector + full-text)
        --folder <path|id>        Restrict to a folder
        --metadata <key=value>    Filter by metadata (repeatable)
        --limit <N>               Max results (default: 200)

    MCP:
      mcp [options] <json>      Call an MCP server tool
        --chat-id / -c <id>       Chat ID (required)
        --message-id / -m <id>    Message ID (required)
        --file / -f <path>        Read JSON from file instead
        --stdin                   Read JSON from stdin

    Scheduled tasks:
      schedule list             List all scheduled tasks
      schedule get <id>         Get details of a task
      schedule create [opts]    Create a new task
        --cron / -c <expr>        Cron expression (required)
        --assistant / -a <id>     Assistant ID (required)
        --prompt / -p <text>      Prompt text (required)
        --chat-id <id>            Chat to continue (optional)
        --disabled                Create disabled
      schedule update <id>      Update a task
        --cron / -c <expr>        Updated cron expression
        --assistant / -a <id>     Updated assistant ID
        --prompt / -p <text>      Updated prompt
        --chat-id <id>            Updated chat ID ('none' to clear)
        --enable / --disable      Toggle task state
      schedule delete <id>      Delete a task

    Shell:
      help [command]            Show help (for a specific command)
      exit / quit               Exit the shell
""")


class UniqueShell(cmd.Cmd):
    """Interactive file explorer shell for the Unique AI Platform."""

    intro = f"Unique File System v{__version__}\nType 'help' for available commands.\n"

    def __init__(self, state: ShellState) -> None:
        super().__init__()
        self.state = state
        self._update_prompt()

    def _update_prompt(self) -> None:
        self.prompt = self.state.prompt

    def _print(self, text: str) -> None:
        print(text)

    # -- Overview help --

    def do_help(self, arg: str) -> None:
        """Show available commands or detailed help for a specific command."""
        if arg:
            super().do_help(arg)
        else:
            self._print(OVERVIEW_HELP)

    # -- Navigation --

    def do_pwd(self, _arg: str) -> None:
        """Print the current working directory.

        Usage: pwd

        Shows the full path of your current location in the Unique
        folder hierarchy.

        Example:
          /Reports> pwd
          /Reports
        """
        self._print(cmd_pwd(self.state))

    def do_cd(self, arg: str) -> None:
        """Change the current working directory.

        Usage: cd <target>

        Accepts a folder name, absolute path, scope ID, ".." or "/".

        Path resolution:
          cd Reports          Relative -- child of current directory
          cd /Company/Reports Absolute -- from root
          cd scope_abc123     Scope ID -- resolved directly
          cd ..               Parent directory
          cd /                Root directory

        Examples:
          /> cd Reports
          /Reports> cd Q1
          /Reports/Q1> cd ..
          /Reports> cd /
          /> cd scope_abc123
          /Company/Reports>
        """
        target = arg.strip()
        if not target:
            target = "/"
        self._print(cmd_cd(self.state, target))
        self._update_prompt()

    def do_ls(self, arg: str) -> None:
        """List folders and files in a directory.

        Usage: ls [target]

        Without arguments, lists the current directory. With an argument,
        lists the specified folder (by name, path, or scope ID).

        Output columns: TYPE  NAME  ID  SIZE  UPDATED

        Examples:
          /Reports> ls
          DIR   Q1/           scope_jkl012              2025-01-15 08:00
          FILE  annual.pdf    cont_mno345     5.4 MB    2025-03-01 12:00
          1 folder(s), 1 file(s)

          /> ls /Reports/Q1
          /> ls scope_abc123
        """
        target = arg.strip() or None
        self._print(cmd_ls(self.state, target))

    # -- Folder operations --

    def do_mkdir(self, arg: str) -> None:
        """Create a new folder under the current directory.

        Usage: mkdir <name>

        Creates a child folder with the given name. Nested paths are
        supported (e.g., "A/B/C" creates the full hierarchy).

        Examples:
          /Reports> mkdir Q2
          Created: /Reports/Q2 (scope_pqr678)

          /Reports> mkdir "2025/Q1"
          Created: /Reports/2025/Q1 (scope_xyz999)
        """
        name = arg.strip()
        if not name:
            self._print("Usage: mkdir <name>")
            return
        self._print(cmd_mkdir(self.state, name))

    def do_rmdir(self, arg: str) -> None:
        """Delete a folder.

        Usage: rmdir <target> [--recursive|-r]

        Deletes a folder by name, path, or scope ID. Without --recursive,
        the folder must be empty. Use -r to delete everything inside.

        Examples:
          /Reports> rmdir Q2
          Deleted folder: /Reports/Q2

          /Reports> rmdir Q1 --recursive
          Deleted folder: /Reports/Q1

          /Reports> rmdir scope_abc123 -r
          Deleted folder: scope_abc123
        """
        parts = shlex.split(arg)
        if not parts:
            self._print("Usage: rmdir <target> [--recursive|-r]")
            return
        target = parts[0]
        recursive = "--recursive" in parts or "-r" in parts
        self._print(cmd_rmdir(self.state, target, recursive=recursive))

    def do_mvdir(self, arg: str) -> None:
        """Rename a folder.

        Usage: mvdir <old_name|scope_id> <new_name>

        Changes the folder's display name. The folder stays in the same
        parent directory.

        Examples:
          /Reports> mvdir Q1 "Q1-2025"
          Renamed folder -> Q1-2025

          /Reports> mvdir scope_abc123 "New Name"
          Renamed folder -> New Name
        """
        parts = shlex.split(arg)
        if len(parts) != 2:
            self._print("Usage: mvdir <old_name|scope_id> <new_name>")
            return
        self._print(cmd_mvdir(self.state, parts[0], parts[1]))

    # -- File operations --

    def do_upload(self, arg: str) -> None:
        """Upload a local file (works like Linux cp).

        Usage: upload <local_path> [destination]

        Uploads a file from your local machine. The destination argument
        works like cp -- it can be a folder, a new filename, or both.
        MIME type is auto-detected from the file extension.

        Destination formats:
          (omitted)       Upload to current dir, keep original name
          .               Upload to current dir, keep original name
          newname.pdf     Upload to current dir, rename to newname.pdf
          subfolder/      Upload into subfolder, keep original name
          ./sub/new.pdf   Upload into sub, rename to new.pdf
          /abs/path/      Upload into absolute folder path
          scope_abc123    Upload into that scope ID

        Examples:
          /Reports> upload ./report.pdf
          Uploaded: report.pdf (cont_abc) to /Reports

          /Reports> upload ./report.pdf "Q1 Report.pdf"
          Uploaded: Q1 Report.pdf (cont_def) to /Reports

          /Reports> upload ./report.pdf Q1/
          Uploaded: report.pdf (cont_ghi) to /Reports/Q1

          /Reports> upload ./report.pdf /Archive/2025/
          Uploaded: report.pdf (cont_jkl) to /Archive/2025
        """
        parts = shlex.split(arg)
        if not parts:
            self._print("Usage: upload <local_path> [destination]")
            return
        local_path = parts[0]
        destination = parts[1] if len(parts) > 1 else None
        self._print(cmd_upload(self.state, local_path, destination))

    def do_download(self, arg: str) -> None:
        """Download a file from the platform to your local machine.

        Usage: download <name|content_id> [local_path]

        Downloads a file identified by its name (matched in the current
        directory) or content ID (cont_...). Saves to the specified local
        path, or the current working directory if omitted.

        Arguments:
          name_or_id    File name or content ID (cont_...)
          local_path    Optional local directory or file path

        Examples:
          /Reports> download annual.pdf
          Downloaded: annual.pdf -> /Users/me/annual.pdf

          /Reports> download annual.pdf ./downloads/
          Downloaded: annual.pdf -> ./downloads/annual.pdf

          /Reports> download cont_mno345 ~/Desktop/
          Downloaded: cont_mno345 -> ~/Desktop/cont_mno345
        """
        parts = shlex.split(arg)
        if not parts:
            self._print("Usage: download <name|content_id> [local_path]")
            return
        name_or_id = parts[0]
        local_dest = parts[1] if len(parts) > 1 else None
        self._print(cmd_download(self.state, name_or_id, local_dest))

    def do_rm(self, arg: str) -> None:
        """Delete a file.

        Usage: rm <name|content_id>

        Permanently deletes a file by its name (matched in the current
        directory) or content ID.

        Examples:
          /Reports> rm annual.pdf
          Deleted: annual.pdf (cont_mno345)

          /Reports> rm cont_xyz789
          Deleted: cont_xyz789 (cont_xyz789)
        """
        name_or_id = arg.strip()
        if not name_or_id:
            self._print("Usage: rm <name|content_id>")
            return
        self._print(cmd_rm(self.state, name_or_id))

    def do_mv(self, arg: str) -> None:
        """Rename a file.

        Usage: mv <old_name|content_id> <new_name>

        Changes the file's display title. The content ID and location
        remain the same.

        Examples:
          /Reports> mv annual.pdf annual-2025.pdf
          Renamed: annual.pdf -> annual-2025.pdf

          /Reports> mv cont_abc123 "New Title.pdf"
          Renamed: cont_abc123 -> New Title.pdf
        """
        parts = shlex.split(arg)
        if len(parts) != 2:
            self._print("Usage: mv <old_name|content_id> <new_name>")
            return
        self._print(cmd_mv_file(self.state, parts[0], parts[1]))

    # -- Search --

    def do_search(self, arg: str) -> None:
        """Search the knowledge base using combined search.

        Usage: search <query> [--folder <path|id>] [--metadata key=value ...] [--limit N]

        Performs a combined (vector + full-text) search across the knowledge
        base. By default searches within the current directory scope with a
        limit of 200 results.

        Options:
          --folder <path|id>     Restrict search to a specific folder
          --metadata <key=value> Filter by metadata field (can be repeated)
          --limit <N>            Maximum number of results (default: 200)

        Examples:
          /Reports> search "revenue growth"
          /Reports> search "quarterly earnings" --folder /Reports/Q1 --limit 10
          /> search "AI strategy" --folder scope_abc123
          /> search "compliance" --metadata department=Legal --metadata year=2025
        """
        parts = shlex.split(arg)
        if not parts:
            self._print(
                "Usage: search <query> [--folder <path|id>] "
                "[--metadata key=value ...] [--limit N]"
            )
            return

        query_parts: list[str] = []
        folder: str | None = None
        metadata: list[tuple[str, str]] = []
        limit = 200

        i = 0
        while i < len(parts):
            if parts[i] in ("--folder", "-f") and i + 1 < len(parts):
                folder = parts[i + 1]
                i += 2
            elif parts[i] in ("--metadata", "-m") and i + 1 < len(parts):
                kv = parts[i + 1]
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    metadata.append((k, v))
                else:
                    self._print(f"Invalid metadata format: {kv} (expected key=value)")
                    return
                i += 2
            elif parts[i] in ("--limit", "-l") and i + 1 < len(parts):
                try:
                    limit = int(parts[i + 1])
                except ValueError:
                    self._print(f"Invalid limit: {parts[i + 1]}")
                    return
                i += 2
            else:
                query_parts.append(parts[i])
                i += 1

        query = " ".join(query_parts)
        if not query:
            self._print(
                "Usage: search <query> [--folder <path|id>] "
                "[--metadata key=value ...] [--limit N]"
            )
            return

        self._print(
            cmd_search(
                self.state,
                query,
                folder=folder,
                metadata=metadata if metadata else None,
                limit=limit,
            )
        )

    # -- MCP --

    def do_mcp(self, arg: str) -> None:
        """Call an MCP server tool with a JSON payload.

        Usage: mcp -c <chat_id> -m <message_id> '<json>'
               mcp -c <chat_id> -m <message_id> --file <path>
               mcp -c <chat_id> -m <message_id> --stdin

        Calls an MCP tool via the Unique platform. The JSON payload
        must contain "name" and (optionally) "arguments":

          {"name": "tool_name", "arguments": {"param": "value"}}

        Options:
          -c / --chat-id <id>      Chat ID (required)
          -m / --message-id <id>   Message ID (required)
          -f / --file <path>       Read JSON payload from a file
          --stdin                  Read JSON payload from stdin

        Examples:
          /> mcp -c chat_123 -m msg_456 '{"name": "search", "arguments": {"q": "test"}}'
          /> mcp -c chat_123 -m msg_456 --file payload.json
        """
        parts = shlex.split(arg)
        if not parts:
            self._print(
                "Usage: mcp -c <chat_id> -m <message_id> '<json>'\n"
                "       mcp -c <chat_id> -m <message_id> --file <path>"
            )
            return

        chat_id: str | None = None
        message_id: str | None = None
        file_path: str | None = None
        use_stdin = False
        positional: list[str] = []

        i = 0
        while i < len(parts):
            if parts[i] in ("--chat-id", "-c") and i + 1 < len(parts):
                chat_id = parts[i + 1]
                i += 2
            elif parts[i] in ("--message-id", "-m") and i + 1 < len(parts):
                message_id = parts[i + 1]
                i += 2
            elif parts[i] in ("--file", "-f") and i + 1 < len(parts):
                file_path = parts[i + 1]
                i += 2
            elif parts[i] == "--stdin":
                use_stdin = True
                i += 1
            else:
                positional.append(parts[i])
                i += 1

        if not chat_id:
            self._print("Error: --chat-id / -c is required.")
            return
        if not message_id:
            self._print("Error: --message-id / -m is required.")
            return

        payload = " ".join(positional) if positional else None

        self._print(
            cmd_mcp(
                self.state,
                chat_id=chat_id,
                message_id=message_id,
                payload=payload,
                file=file_path,
                stdin=use_stdin,
            )
        )

    # -- Scheduled tasks --

    def do_schedule(self, arg: str) -> None:
        """Manage cron-based scheduled tasks.

        Usage: schedule <subcommand> [options]

        Subcommands:
          list                    List all scheduled tasks
          get <task_id>           Get details of a task
          create [options]        Create a new scheduled task
          update <task_id> [opts] Update an existing task
          delete <task_id>        Delete a task

        Create options:
          --cron / -c <expr>      Cron expression (required)
          --assistant / -a <id>   Assistant ID (required)
          --prompt / -p <text>    Prompt text (required)
          --chat-id <id>          Chat to continue (optional)
          --disabled              Create in disabled state

        Update options:
          --cron / -c <expr>      Updated cron expression
          --assistant / -a <id>   Updated assistant ID
          --prompt / -p <text>    Updated prompt
          --chat-id <id>          Updated chat ID ('none' to clear)
          --enable                Enable the task
          --disable               Disable the task

        Examples:
          /> schedule list
          /> schedule get clx3ghi4f0003mnopqr345678
          /> schedule create -c "0 9 * * 1-5" -a clx1abc -p "Daily report"
          /> schedule update clx3ghi4f --disable
          /> schedule delete clx3ghi4f0003mnopqr345678
        """
        parts = shlex.split(arg)
        if not parts:
            self._print(
                "Usage: schedule <list|get|create|update|delete> [options]\n"
                "Type 'help schedule' for details."
            )
            return

        subcmd = parts[0]
        rest = parts[1:]

        if subcmd == "list":
            self._print(cmd_schedule_list(self.state))

        elif subcmd == "get":
            if not rest:
                self._print("Usage: schedule get <task_id>")
                return
            self._print(cmd_schedule_get(self.state, rest[0]))

        elif subcmd == "create":
            self._schedule_create(rest)

        elif subcmd == "update":
            if not rest:
                self._print("Usage: schedule update <task_id> [options]")
                return
            self._schedule_update(rest[0], rest[1:])

        elif subcmd == "delete":
            if not rest:
                self._print("Usage: schedule delete <task_id>")
                return
            self._print(cmd_schedule_delete(self.state, rest[0]))

        else:
            self._print(
                f"Unknown subcommand: {subcmd}\n"
                "Usage: schedule <list|get|create|update|delete> [options]"
            )

    def _schedule_create(self, parts: list[str]) -> None:
        """Parse and execute schedule create."""
        cron: str | None = None
        assistant_id: str | None = None
        prompt: str | None = None
        chat_id: str | None = None
        disabled = False

        i = 0
        while i < len(parts):
            if parts[i] in ("--cron", "-c") and i + 1 < len(parts):
                cron = parts[i + 1]
                i += 2
            elif parts[i] in ("--assistant", "-a") and i + 1 < len(parts):
                assistant_id = parts[i + 1]
                i += 2
            elif parts[i] in ("--prompt", "-p") and i + 1 < len(parts):
                prompt = parts[i + 1]
                i += 2
            elif parts[i] == "--chat-id" and i + 1 < len(parts):
                chat_id = parts[i + 1]
                i += 2
            elif parts[i] == "--disabled":
                disabled = True
                i += 1
            else:
                self._print(f"Unknown option: {parts[i]}")
                return

        if not cron or not assistant_id or not prompt:
            self._print(
                "Usage: schedule create --cron <expr> --assistant <id> --prompt <text> "
                "[--chat-id <id>] [--disabled]"
            )
            return

        self._print(
            cmd_schedule_create(
                self.state,
                cron=cron,
                assistant_id=assistant_id,
                prompt=prompt,
                chat_id=chat_id,
                enabled=not disabled,
            )
        )

    def _schedule_update(self, task_id: str, parts: list[str]) -> None:
        """Parse and execute schedule update."""
        cron: str | None = None
        assistant_id: str | None = None
        prompt: str | None = None
        chat_id: str | None = None
        enable = False
        disable = False

        i = 0
        while i < len(parts):
            if parts[i] in ("--cron", "-c") and i + 1 < len(parts):
                cron = parts[i + 1]
                i += 2
            elif parts[i] in ("--assistant", "-a") and i + 1 < len(parts):
                assistant_id = parts[i + 1]
                i += 2
            elif parts[i] in ("--prompt", "-p") and i + 1 < len(parts):
                prompt = parts[i + 1]
                i += 2
            elif parts[i] == "--chat-id" and i + 1 < len(parts):
                chat_id = "" if parts[i + 1].lower() == "none" else parts[i + 1]
                i += 2
            elif parts[i] == "--enable":
                enable = True
                i += 1
            elif parts[i] == "--disable":
                disable = True
                i += 1
            else:
                self._print(f"Unknown option: {parts[i]}")
                return

        if enable and disable:
            self._print("schedule: cannot use --enable and --disable together")
            return

        enabled: bool | None = None
        if enable:
            enabled = True
        elif disable:
            enabled = False

        self._print(
            cmd_schedule_update(
                self.state,
                task_id,
                cron=cron,
                assistant_id=assistant_id,
                prompt=prompt,
                chat_id=chat_id,
                enabled=enabled,
            )
        )

    # -- Shell control --

    def do_exit(self, _arg: str) -> bool:
        """Exit the interactive shell. Ctrl+D also works."""
        return True

    def do_quit(self, _arg: str) -> bool:
        """Exit the interactive shell. Same as 'exit'."""
        return True

    do_EOF = do_exit

    def emptyline(self) -> bool:
        return False

    def default(self, line: str) -> None:
        self._print(
            f"Unknown command: {line.split()[0]}. Type 'help' for available commands."
        )
