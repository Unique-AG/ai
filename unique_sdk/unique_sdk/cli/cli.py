"""Click entry point with one-shot subcommands and interactive shell mode."""

from __future__ import annotations

import click

from unique_sdk.cli import __version__
from unique_sdk.cli.commands.files import cmd_download, cmd_mv_file, cmd_rm, cmd_upload
from unique_sdk.cli.commands.folders import cmd_mkdir, cmd_mvdir, cmd_rmdir
from unique_sdk.cli.commands.mcp import cmd_mcp
from unique_sdk.cli.commands.navigation import cmd_cd, cmd_ls, cmd_pwd
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
  UNIQUE_API_KEY      API key for the Unique platform
  UNIQUE_APP_ID       Application identifier
  UNIQUE_USER_ID      User ID for API requests
  UNIQUE_COMPANY_ID   Company ID for API requests

\b
Optional:
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
