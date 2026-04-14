"""Click entry point with one-shot subcommands and interactive shell mode."""

from __future__ import annotations

import click

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
from unique_sdk.cli.config import load_config
from unique_sdk.cli.shell import UniqueShell
from unique_sdk.cli.state import ShellState

MAIN_HELP = """\
Unique CLI -- Linux-like file explorer for the Unique AI Platform.

Browse, manage, and search files and folders in the Unique knowledge base
using familiar commands (cd, ls, mkdir, rm, mv, etc.) as if connected to
a remote server via SSH.

\b
Modes:
  Interactive shell   Run without a subcommand to enter the REPL.
  One-shot command    Run with a subcommand (e.g. unique-cli ls /Reports).

\b
Required environment variables:
  UNIQUE_USER_ID      User ID for API requests
  UNIQUE_COMPANY_ID   Company ID for API requests

\b
Optional:
  UNIQUE_API_KEY      API key (not needed on localhost / secured cluster)
  UNIQUE_APP_ID       Application identifier (not needed on localhost / secured cluster)
  UNIQUE_API_BASE     API base URL (default: https://gateway.unique.app/public/chat-gen2)

\b
Path formats accepted by all commands:
  Reports             Relative name (resolved from current directory)
  /Company/Reports    Absolute path (from root)
  scope_abc123        Scope ID (resolved directly)

\b
File identifiers:
  report.pdf          File name (matched in current directory)
  cont_abc123         Content ID (used directly)

\b
Examples:
  unique-cli                        Launch interactive shell
  unique-cli ls                     List root folders
  unique-cli ls /Reports            List a specific folder
  unique-cli search "revenue" -l 50 Search with custom limit
  unique-cli upload ./file.pdf      Upload to current folder
  unique-cli download cont_abc123   Download by content ID
"""


class LazyState:
    """Lazily initializes ShellState on first access so --help works without env vars."""

    @staticmethod
    def get(ctx: click.Context) -> ShellState:
        if ctx.obj is None:
            config = load_config()
            ctx.obj = ShellState(config)
        return ctx.obj


@click.group(invoke_without_command=True, help=MAIN_HELP)
@click.version_option(version=__version__, prog_name="unique-cli")
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        state = LazyState.get(ctx)
        shell = UniqueShell(state)
        shell.intro = (
            f"Unique File System v{__version__}\n"
            f"Connected as {state.config.user_id} @ {state.config.company_id}\n"
            f"Type 'help' for available commands.\n"
        )
        shell.cmdloop()


@main.command()
@click.pass_context
def pwd(ctx: click.Context) -> None:
    """Print the current working directory path.

    \b
    Shows the full path of your position in the Unique folder
    hierarchy. At startup the directory is always /.
    """
    click.echo(cmd_pwd(LazyState.get(ctx)))


@main.command()
@click.argument("target", default="/")
@click.pass_context
def cd(ctx: click.Context, target: str) -> None:
    """Change the current working directory.

    \b
    TARGET can be:
      folder name       Resolved relative to the current directory
      /absolute/path    Resolved from root
      scope_abc123      Scope ID, resolved directly
      ..                Parent directory
      /                 Root directory

    \b
    Examples:
      unique-cli cd Reports
      unique-cli cd /Company/Reports/Q1
      unique-cli cd scope_abc123
    """
    click.echo(cmd_cd(LazyState.get(ctx), target))


@main.command()
@click.argument("target", required=False, default=None)
@click.pass_context
def ls(ctx: click.Context, target: str | None) -> None:
    """List folders and files in a directory.

    \b
    Without TARGET, lists the current directory. With TARGET, lists
    the specified folder (by name, absolute path, or scope ID).

    \b
    Output columns: TYPE  NAME  ID  SIZE  UPDATED
      DIR   Reports/     scope_abc123              2025-03-01 10:00
      FILE  readme.txt   cont_ghi789     1.2 KB    2025-03-10 09:00

    \b
    Examples:
      unique-cli ls              List root folders
      unique-cli ls /Reports     List a specific path
      unique-cli ls scope_abc    List by scope ID
    """
    click.echo(cmd_ls(LazyState.get(ctx), target))


@main.command()
@click.argument("name")
@click.pass_context
def mkdir(ctx: click.Context, name: str) -> None:
    """Create a new folder under the current directory.

    \b
    NAME is the folder name to create. Nested paths are supported
    (e.g., "A/B/C" creates the full hierarchy).

    \b
    Examples:
      unique-cli mkdir Q2
      unique-cli mkdir "2025/Q1"
    """
    click.echo(cmd_mkdir(LazyState.get(ctx), name))


@main.command()
@click.argument("target")
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Delete folder and all its contents recursively.",
)
@click.pass_context
def rmdir(ctx: click.Context, target: str, recursive: bool) -> None:
    """Delete a folder by name, path, or scope ID.

    \b
    Without --recursive, the folder must be empty. Use -r to delete
    the folder and everything inside it.

    \b
    Examples:
      unique-cli rmdir Q2
      unique-cli rmdir /Reports/Q1 --recursive
      unique-cli rmdir scope_abc123 -r
    """
    click.echo(cmd_rmdir(LazyState.get(ctx), target, recursive=recursive))


@main.command()
@click.argument("old_name")
@click.argument("new_name")
@click.pass_context
def mvdir(ctx: click.Context, old_name: str, new_name: str) -> None:
    """Rename a folder.

    \b
    Changes the folder's display name without moving it. OLD_NAME
    can be a folder name, path, or scope ID.

    \b
    Examples:
      unique-cli mvdir Q1 "Q1-2025"
      unique-cli mvdir scope_abc123 "New Name"
    """
    click.echo(cmd_mvdir(LazyState.get(ctx), old_name, new_name))


@main.command()
@click.argument("local_path")
@click.argument("destination", required=False, default=None)
@click.pass_context
def upload(ctx: click.Context, local_path: str, destination: str | None) -> None:
    """Upload a local file (works like Linux cp).

    \b
    Uploads LOCAL_PATH to the Unique platform. DESTINATION works like
    the target in cp -- it can be a folder path, a new filename, or
    a combination of both. MIME type is auto-detected.

    \b
    Destination formats:
      (omitted)       Current dir, keep original name
      .               Current dir, keep original name
      newname.pdf     Current dir, rename to newname.pdf
      subfolder/      Upload into subfolder, keep name
      ./sub/new.pdf   Upload into sub, rename to new.pdf
      /abs/path/      Upload into absolute folder path
      scope_abc123    Upload into that scope ID

    \b
    Examples:
      unique-cli upload ./report.pdf
      unique-cli upload ./report.pdf "Q1 Report.pdf"
      unique-cli upload ./report.pdf Q1/
      unique-cli upload ./report.pdf /Archive/2025/
    """
    click.echo(cmd_upload(LazyState.get(ctx), local_path, destination))


@main.command()
@click.argument("name_or_id")
@click.argument("local_dest", required=False, default=None)
@click.pass_context
def download(ctx: click.Context, name_or_id: str, local_dest: str | None) -> None:
    """Download a file to your local machine.

    \b
    NAME_OR_ID is a file name (matched in the current directory) or
    a content ID (cont_...) which is resolved directly.

    \b
    LOCAL_DEST is an optional path (directory or file) to save to.
    Defaults to the current local working directory.

    \b
    Examples:
      unique-cli download annual.pdf
      unique-cli download annual.pdf ./downloads/
      unique-cli download cont_abc123 ~/Desktop/
    """
    click.echo(cmd_download(LazyState.get(ctx), name_or_id, local_dest))


@main.command()
@click.argument("name_or_id")
@click.pass_context
def rm(ctx: click.Context, name_or_id: str) -> None:
    """Delete a file by name or content ID.

    \b
    NAME_OR_ID is a file name (matched in the current directory) or
    a content ID (cont_...).

    \b
    Examples:
      unique-cli rm report.pdf
      unique-cli rm cont_abc123
    """
    click.echo(cmd_rm(LazyState.get(ctx), name_or_id))


@main.command()
@click.argument("old_name")
@click.argument("new_name")
@click.pass_context
def mv(ctx: click.Context, old_name: str, new_name: str) -> None:
    """Rename a file.

    \b
    Changes the file's display title without changing its content ID
    or location. OLD_NAME can be a file name or content ID.

    \b
    Examples:
      unique-cli mv annual.pdf annual-2025.pdf
      unique-cli mv cont_abc123 "New Title.pdf"
    """
    click.echo(cmd_mv_file(LazyState.get(ctx), old_name, new_name))


@main.command()
@click.argument("query")
@click.option(
    "--folder",
    "-f",
    default=None,
    help="Restrict search to a folder (path, name, or scope ID). Defaults to current directory.",
)
@click.option(
    "--metadata",
    "-m",
    multiple=True,
    help="Metadata filter as key=value. Can be repeated for AND logic.",
)
@click.option(
    "--limit",
    "-l",
    default=200,
    show_default=True,
    help="Maximum number of results to return.",
)
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    folder: str | None,
    metadata: tuple[str, ...],
    limit: int,
) -> None:
    """Search the knowledge base using combined (vector + full-text) search.

    \b
    QUERY is the search text. Results are ranked by relevance using
    both semantic similarity and keyword matching.

    \b
    By default, searches within the current directory scope with up
    to 200 results. Use --folder to target a different folder, and
    --metadata to filter by custom metadata fields.

    \b
    Examples:
      unique-cli search "revenue growth"
      unique-cli search "earnings" --folder /Reports/Q1 --limit 50
      unique-cli search "compliance" -f scope_abc123
      unique-cli search "audit" -m department=Legal -m year=2025
    """
    state = LazyState.get(ctx)
    parsed_metadata: list[tuple[str, str]] | None = None
    if metadata:
        parsed_metadata = []
        for kv in metadata:
            if "=" not in kv:
                click.echo(f"Invalid metadata format: {kv} (expected key=value)")
                return
            k, v = kv.split("=", 1)
            parsed_metadata.append((k, v))

    click.echo(
        cmd_search(state, query, folder=folder, metadata=parsed_metadata, limit=limit)
    )


@main.command()
@click.argument("payload", required=False, default=None)
@click.option(
    "--chat-id",
    "-c",
    required=True,
    help="Chat ID for the MCP tool call context.",
)
@click.option(
    "--message-id",
    "-m",
    required=True,
    help="Message ID for the MCP tool call context.",
)
@click.option(
    "--file",
    "-f",
    "file_path",
    default=None,
    type=click.Path(exists=True),
    help="Read JSON payload from a file instead of a positional argument.",
)
@click.option(
    "--stdin",
    "use_stdin",
    is_flag=True,
    help="Read JSON payload from stdin.",
)
@click.pass_context
def mcp(
    ctx: click.Context,
    payload: str | None,
    chat_id: str,
    message_id: str,
    file_path: str | None,
    use_stdin: bool,
) -> None:
    """Call an MCP server tool with a JSON payload.

    \b
    PAYLOAD is a JSON string containing the tool name and arguments:
      {"name": "tool_name", "arguments": {"param": "value"}}

    \b
    The JSON is forwarded 1:1 to the MCP call-tool API. Chat ID and
    message ID are provided as separate flags to identify the
    conversation context.

    \b
    Input sources (exactly one required):
      PAYLOAD              Inline JSON string
      --file / -f PATH     Read JSON from a file
      --stdin              Read JSON from stdin

    \b
    Examples:
      unique-cli mcp -c chat_123 -m msg_456 \\
        '{"name": "search", "arguments": {"query": "test"}}'

      unique-cli mcp -c chat_123 -m msg_456 --file payload.json

      cat payload.json | unique-cli mcp -c chat_123 -m msg_456 --stdin
    """
    click.echo(
        cmd_mcp(
            LazyState.get(ctx),
            chat_id=chat_id,
            message_id=message_id,
            payload=payload,
            file=file_path,
            stdin=use_stdin,
        )
    )


# -- Scheduled Tasks -------------------------------------------------------


@main.group()
def schedule() -> None:
    """Manage cron-based scheduled tasks.

    \b
    Scheduled tasks trigger an assistant on a recurring schedule
    defined by a cron expression. A Kubernetes CronJob evaluates all
    enabled tasks every minute and triggers execution for those whose
    cron expression matches the current time.

    \b
    Subcommands:
      list      List all scheduled tasks
      get       Get details of a single task
      create    Create a new scheduled task
      update    Update an existing task
      delete    Delete a task
    """


@schedule.command(name="list")
@click.pass_context
def schedule_list(ctx: click.Context) -> None:
    """List all scheduled tasks for the authenticated user.

    \b
    Shows a table of all tasks with their status, cron expression,
    assistant, prompt snippet, ID, and last run time.

    \b
    Examples:
      unique-cli schedule list
    """
    click.echo(cmd_schedule_list(LazyState.get(ctx)))


@schedule.command(name="get")
@click.argument("task_id")
@click.pass_context
def schedule_get(ctx: click.Context, task_id: str) -> None:
    """Get details of a scheduled task by ID.

    \b
    TASK_ID is the scheduled task identifier.

    \b
    Examples:
      unique-cli schedule get clx3ghi4f0003mnopqr345678
    """
    click.echo(cmd_schedule_get(LazyState.get(ctx), task_id))


@schedule.command(name="create")
@click.option(
    "--cron",
    "-c",
    required=True,
    help='5-field cron expression (e.g. "*/15 * * * *").',
)
@click.option(
    "--assistant",
    "-a",
    "assistant_id",
    required=True,
    help="ID of the assistant to execute on each trigger.",
)
@click.option(
    "--prompt",
    "-p",
    required=True,
    help="Prompt text sent to the assistant on each trigger.",
)
@click.option(
    "--chat-id",
    default=None,
    help="Optional chat ID to continue. If omitted, a new chat is created each run.",
)
@click.option(
    "--disabled",
    is_flag=True,
    default=False,
    help="Create the task in a disabled state.",
)
@click.pass_context
def schedule_create(
    ctx: click.Context,
    cron: str,
    assistant_id: str,
    prompt: str,
    chat_id: str | None,
    disabled: bool,
) -> None:
    """Create a new scheduled task.

    \b
    Defines a cron schedule, an assistant, and a prompt. The task
    will execute the assistant with the given prompt on every cron
    match.

    \b
    Cron expression format (5 fields):
      minute hour day-of-month month day-of-week

    \b
    Examples:
      unique-cli schedule create \\
        --cron "0 9 * * 1-5" \\
        --assistant clx1abc2d0001abcdef123456 \\
        --prompt "Generate the daily sales report"

      unique-cli schedule create \\
        -c "*/15 * * * *" -a clx1abc -p "Check inbox" --disabled
    """
    click.echo(
        cmd_schedule_create(
            LazyState.get(ctx),
            cron=cron,
            assistant_id=assistant_id,
            prompt=prompt,
            chat_id=chat_id,
            enabled=not disabled,
        )
    )


@schedule.command(name="update")
@click.argument("task_id")
@click.option("--cron", "-c", default=None, help="Updated cron expression.")
@click.option(
    "--assistant", "-a", "assistant_id", default=None, help="Updated assistant ID."
)
@click.option("--prompt", "-p", default=None, help="Updated prompt text.")
@click.option("--chat-id", default=None, help="Updated chat ID (use 'none' to clear).")
@click.option("--enable", is_flag=True, default=False, help="Enable the task.")
@click.option("--disable", is_flag=True, default=False, help="Disable the task.")
@click.pass_context
def schedule_update(
    ctx: click.Context,
    task_id: str,
    cron: str | None,
    assistant_id: str | None,
    prompt: str | None,
    chat_id: str | None,
    enable: bool,
    disable: bool,
) -> None:
    """Update an existing scheduled task.

    \b
    TASK_ID is the scheduled task identifier. Only the fields you
    provide will be changed; everything else stays the same.

    \b
    Examples:
      unique-cli schedule update clx3ghi4f --cron "0 9 * * 1-5"
      unique-cli schedule update clx3ghi4f --disable
      unique-cli schedule update clx3ghi4f --enable --prompt "New prompt"
      unique-cli schedule update clx3ghi4f --chat-id none
    """
    if enable and disable:
        click.echo("schedule: cannot use --enable and --disable together")
        return

    enabled: bool | None = None
    if enable:
        enabled = True
    elif disable:
        enabled = False

    resolved_chat_id = chat_id
    if chat_id and chat_id.lower() == "none":
        resolved_chat_id = ""

    click.echo(
        cmd_schedule_update(
            LazyState.get(ctx),
            task_id,
            cron=cron,
            assistant_id=assistant_id,
            prompt=prompt,
            chat_id=resolved_chat_id,
            enabled=enabled,
        )
    )


@schedule.command(name="delete")
@click.argument("task_id")
@click.pass_context
def schedule_delete(ctx: click.Context, task_id: str) -> None:
    """Delete a scheduled task by ID.

    \b
    TASK_ID is the scheduled task identifier. This action cannot
    be undone.

    \b
    Examples:
      unique-cli schedule delete clx3ghi4f0003mnopqr345678
    """
    click.echo(cmd_schedule_delete(LazyState.get(ctx), task_id))
