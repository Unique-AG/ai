"""Click entry point with one-shot subcommands and interactive shell mode."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import click

from unique_sdk.cli import __version__
from unique_sdk.cli.commands.browser import (
    cmd_browser_action,
    cmd_browser_control,
    cmd_browser_download,
    cmd_browser_status,
)
from unique_sdk.cli.commands.browser import (
    is_error_output as _is_browser_error_output,
)
from unique_sdk.cli.commands.cite_file import cmd_cite_file
from unique_sdk.cli.commands.cite_file import (
    is_error_output as _is_cite_error_output,
)
from unique_sdk.cli.commands.dynamic_frontend import (
    cmd_dynamic_frontend_delete,
    cmd_dynamic_frontend_deploy,
    cmd_dynamic_frontend_list,
)
from unique_sdk.cli.commands.elicitation import (
    DEFAULT_WAIT_TIMEOUT_SECONDS,
    cmd_elicit_ask,
    cmd_elicit_create,
    cmd_elicit_get,
    cmd_elicit_pending,
    cmd_elicit_respond,
    cmd_elicit_wait,
)
from unique_sdk.cli.commands.files import (
    cmd_download,
    cmd_mv_file,
    cmd_restore_version,
    cmd_rm,
    cmd_upload,
    cmd_versions,
)
from unique_sdk.cli.commands.files import (
    is_permission_denied_output as _is_permission_denied_output,
)
from unique_sdk.cli.commands.folders import cmd_mkdir, cmd_mvdir, cmd_rmdir
from unique_sdk.cli.commands.mcp import cmd_mcp
from unique_sdk.cli.commands.navigation import cmd_cd, cmd_ls, cmd_pwd
from unique_sdk.cli.commands.read import cmd_read
from unique_sdk.cli.commands.read import (
    is_error_output as _is_read_error_output,
)
from unique_sdk.cli.commands.scheduled_tasks import (
    cmd_schedule_create,
    cmd_schedule_delete,
    cmd_schedule_get,
    cmd_schedule_list,
    cmd_schedule_update,
)
from unique_sdk.cli.commands.search import (
    cmd_search,
    cmd_uploaded_search,
)
from unique_sdk.cli.commands.search import (
    is_error_output as _is_search_error_output,
)
from unique_sdk.cli.commands.search import (
    is_uploaded_search_error_output as _is_uploaded_search_error_output,
)
from unique_sdk.cli.commands.subagent import cmd_subagent
from unique_sdk.cli.commands.subagent import (
    is_error_output as _is_subagent_error_output,
)
from unique_sdk.cli.commands.web_search import (
    cmd_web_crawl,
    cmd_web_search,
)
from unique_sdk.cli.commands.web_search import (
    is_error_output as _is_web_search_error_output,
)
from unique_sdk.cli.commands.web_search_config import ENV_CONFIG_PATH
from unique_sdk.cli.config import load_config
from unique_sdk.cli.identity import TurnIdentityError, resolve_message_id
from unique_sdk.cli.shell import UniqueShell
from unique_sdk.cli.state import ShellState

_DYNAMIC_FRONTEND_ERROR_PREFIX = "dynamic-frontend "


def _resolve_cli_message_id(
    ctx: click.Context,
    explicit: str | None,
    *,
    required: bool = False,
) -> str | None:
    """Resolve message id for Click commands; exit on turn-identity errors.

    When *required* is True and no source yields a value, exits with code 2.
    """
    try:
        resolved = resolve_message_id(explicit)
    except TurnIdentityError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(2)
    if required and not resolved:
        click.echo(
            "Error: message id is required. Pass --message-id, or set "
            "UNIQUE_TURN_IDENTITY_FILE / UNIQUE_MESSAGE_ID.",
            err=True,
        )
        ctx.exit(2)
    return resolved


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
  /Reports/report.pdf File path (absolute or relative)
  cont_abc123         Content ID (used directly)

\b
Examples:
  unique-cli                        Launch interactive shell
  unique-cli ls                     List root folders
  unique-cli ls /Reports            List a specific folder
  unique-cli search "revenue" -l 50 Search with custom limit
  unique-cli upload ./file.pdf      Upload versioned to current folder
  unique-cli download cont_abc123   Download by content ID
  unique-cli versions cont_abc123   List archived file versions
  unique-cli restore-version cver_1 Restore a file from a version
  unique-cli elicit ask "Which?"    Ask the user a question synchronously
  unique-cli subagent Legal "Review" Invoke a connected space/subagent
  unique-cli web-search search "x"  Search the web via the public API
  unique-cli web-search crawl URL   Crawl a URL via the public API
  unique-cli dynamic-frontend list  List manageable Dynamic Frontend spaces
  unique-cli browser get-dom        Read the user's live Chrome tab (a11y tree)
"""


class LazyState:
    """Lazily initializes ShellState on first access so --help works without env vars."""

    @staticmethod
    def get(ctx: click.Context) -> ShellState:
        if ctx.obj is None:
            config = load_config()
            ctx.obj = ShellState(config)
        return ctx.obj


def emit(
    output: str,
    *,
    is_error: Callable[[str], bool] = _is_permission_denied_output,
) -> None:
    """Print a command's *output* and exit non-zero when it is an error.

    Errors (e.g. a scope denial) are written to stderr and raise
    ``SystemExit(1)`` so agent ``&&`` chains stop cleanly; successful output
    goes to stdout. The default predicate matches the ``<cmd>: permission
    denied`` shape shared by the scope-gated commands; pass ``is_error`` for
    commands with their own error-detection helper (cite/read/search/...).
    """
    if is_error(output):
        click.echo(output, err=True)
        raise SystemExit(1)
    click.echo(output)


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
    output = cmd_ls(LazyState.get(ctx), target)
    emit(output)


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
    output = cmd_mkdir(LazyState.get(ctx), name)
    emit(output)


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
    output = cmd_rmdir(LazyState.get(ctx), target, recursive=recursive)
    emit(output)


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
    output = cmd_mvdir(LazyState.get(ctx), old_name, new_name)
    emit(output)


@main.command()
@click.argument("local_path")
@click.argument("destination", required=False, default=None)
@click.pass_context
def upload(ctx: click.Context, local_path: str, destination: str | None) -> None:
    """Upload a local file with versioning enabled (works like Linux cp).

    \b
    Uploads LOCAL_PATH to the Unique platform with immutable versioning
    enabled. DESTINATION works like the target in cp -- it can be a
    folder path, a new filename, or a combination of both. MIME type is
    auto-detected.

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
    output = cmd_upload(LazyState.get(ctx), local_path, destination)
    emit(output)


@main.command()
@click.argument("name_or_id")
@click.option("--skip", type=int, default=None, help="Number of versions to skip.")
@click.option("--take", type=int, default=None, help="Number of versions to return.")
@click.pass_context
def versions(
    ctx: click.Context,
    name_or_id: str,
    skip: int | None,
    take: int | None,
) -> None:
    """List archived versions for a file.

    \b
    NAME_OR_ID is a file path, a file name matched in the current
    directory, or a content ID (cont_...) which is resolved directly.

    \b
    Examples:
      unique-cli versions report.pdf
      unique-cli versions /Reports/Q1/report.pdf
      unique-cli versions cont_abc123 --take 10
    """
    output = cmd_versions(LazyState.get(ctx), name_or_id, skip=skip, take=take)
    emit(output)


@main.command(name="restore-version")
@click.argument("content_version_id")
@click.pass_context
def restore_version(ctx: click.Context, content_version_id: str) -> None:
    """Restore a file from a content version ID.

    \b
    CONTENT_VERSION_ID is returned by `unique-cli versions`.

    \b
    Examples:
      unique-cli restore-version cver_abc123
    """
    output = cmd_restore_version(LazyState.get(ctx), content_version_id)
    emit(output)


@main.command()
@click.argument("name_or_id")
@click.argument("local_dest", required=False, default=None)
@click.pass_context
def download(ctx: click.Context, name_or_id: str, local_dest: str | None) -> None:
    """Download a file to your local machine.

    \b
    NAME_OR_ID is a file path, a file name matched in the current
    directory, or a content ID (cont_...) which is resolved directly.

    \b
    LOCAL_DEST is an optional path (directory or file) to save to.
    Defaults to the current local working directory.

    \b
    Examples:
      unique-cli download annual.pdf
      unique-cli download /Reports/Q1/annual.pdf
      unique-cli download annual.pdf ./downloads/
      unique-cli download cont_abc123 ~/Desktop/
    """
    output = cmd_download(LazyState.get(ctx), name_or_id, local_dest)
    emit(output)


@main.command(name="cite")
@click.argument("name_or_id")
@click.option(
    "--pages",
    "-p",
    default=None,
    help="Page numbers to cite: '3-7' or '1,3,5'. Omit for whole-file.",
)
@click.option(
    "--read-method",
    "-m",
    "read_method",
    required=True,
    help=(
        "How you read the cited source: 'text' (page/document text, e.g. "
        "pdftotext, PyMuPDF, MarkItDown), 'vision' (page rendered as an image "
        "and read visually), or 'indexed' (read via the platform index with "
        "unique-cli read). Common tool names (pdftotext, fitz, ocr, ...) are "
        "accepted and normalized. Use separate cite calls when different pages "
        "were read by different methods."
    ),
)
@click.pass_context
def cite(
    ctx: click.Context,
    name_or_id: str,
    pages: str | None,
    read_method: str,
) -> None:
    """Declare page citations for a file.

    \b
    Registers [filesourceN] markers for pages you referenced in your answer.
    Does NOT read or extract the file — use your own tools for that.
    NAME_OR_ID can be a file path, current-directory file name, or content ID.
    --read-method is mandatory: it records how you read the page(s).
    --pages is optional; omit it to cite the whole file (e.g. non-paginated
    formats).

    \b
    Examples:
      unique-cli cite report.pdf --pages 3,5,7 --read-method text
      unique-cli cite /Reports/Q1/report.pdf --pages 3,5,7 --read-method vision
      unique-cli cite cont_abc123 --pages 1-4 --read-method indexed
      unique-cli cite notes.docx --read-method text
    """
    output = cmd_cite_file(LazyState.get(ctx), name_or_id, pages, read_method)
    emit(output, is_error=_is_cite_error_output)


@main.command(name="read")
@click.argument("cont_id")
@click.option(
    "--page",
    "-p",
    type=int,
    default=None,
    help="Read a single page (shorthand for --from-page N --to-page N).",
)
@click.option(
    "--from-page",
    type=int,
    default=None,
    help="First page to include (inclusive).",
)
@click.option(
    "--to-page",
    type=int,
    default=None,
    help="Last page to include (inclusive).",
)
@click.option(
    "--max-chars",
    type=int,
    default=None,
    help="Truncate the printed text to at most N characters.",
)
@click.pass_context
def read_cmd(
    ctx: click.Context,
    cont_id: str,
    page: int | None,
    from_page: int | None,
    to_page: int | None,
    max_chars: int | None,
) -> None:
    """Read indexed text chunks for a known content ID.

    \b
    CONT_ID must be a content ID (cont_...) obtained from a prior `ls` or
    `search` result. Retrieves every indexed chunk directly from the database
    — no vector search, no query string needed.

    \b
    Use `search` when you need to find documents by topic or keyword.
    Use `read` when you already know the content ID and want the full text.

    \b
    Restrict to a page range with --page (single page) or --from-page/--to-page.
    A chunk spanning pages 2-4 is returned for any overlapping request; files
    without page numbers (e.g. plain text/markdown) are returned only without a
    page range.

    \b
    Examples:
      unique-cli read cont_abc123
      unique-cli read cont_abc123 --page 12
      unique-cli read cont_abc123 --from-page 5 --to-page 9
      unique-cli read cont_abc123 --to-page 3 --max-chars 8000
    """
    if page is not None and (from_page is not None or to_page is not None):
        click.echo(
            "read: use either --page or --from-page/--to-page, not both", err=True
        )
        raise SystemExit(1)
    if page is not None:
        from_page = page
        to_page = page
    output = cmd_read(
        LazyState.get(ctx),
        cont_id,
        from_page=from_page,
        to_page=to_page,
        max_chars=max_chars,
    )
    emit(output, is_error=_is_read_error_output)


@main.group(name="dynamic-frontend")
def dynamic_frontend() -> None:
    """Deploy, list, and delete Dynamic Frontend spaces."""


@dynamic_frontend.command(name="deploy")
@click.option(
    "--file",
    "file_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to an upload-ready Dynamic Frontend ZIP bundle.",
)
@click.option(
    "--content-id",
    default=None,
    help="Existing Knowledge Base content id for the ZIP bundle.",
)
@click.option(
    "--name",
    default=None,
    help="Space display name. Required when creating; optional rename when updating.",
)
@click.option(
    "--space-id", default=None, help="Existing Dynamic Frontend space id to update."
)
@click.option(
    "--json", "output_json", is_flag=True, default=False, help="Print raw JSON."
)
@click.pass_context
def dynamic_frontend_deploy(
    ctx: click.Context,
    file_path: str | None,
    content_id: str | None,
    name: str | None,
    space_id: str | None,
    output_json: bool,
) -> None:
    """Create or update a Dynamic Frontend space.

    \b
    Examples:
      unique-cli dynamic-frontend deploy --file ./app.zip --name "Revenue Dashboard"
      unique-cli dynamic-frontend deploy --content-id content_123 --name "Revenue Dashboard"
      unique-cli dynamic-frontend deploy --space-id assistant_123 --file ./app.zip
    """
    output = cmd_dynamic_frontend_deploy(
        LazyState.get(ctx),
        file=file_path,
        content_id=content_id,
        name=name,
        space_id=space_id,
        output_json=output_json,
    )
    click.echo(output)
    if output.startswith(_DYNAMIC_FRONTEND_ERROR_PREFIX):
        ctx.exit(1)


@dynamic_frontend.command(name="list")
@click.option(
    "--json", "output_json", is_flag=True, default=False, help="Print raw JSON."
)
@click.pass_context
def dynamic_frontend_list(ctx: click.Context, output_json: bool) -> None:
    """List Dynamic Frontend spaces the current user can manage."""
    output = cmd_dynamic_frontend_list(LazyState.get(ctx), output_json=output_json)
    click.echo(output)
    if output.startswith(_DYNAMIC_FRONTEND_ERROR_PREFIX):
        ctx.exit(1)


@dynamic_frontend.command(name="delete")
@click.argument("space_id")
@click.option(
    "--json", "output_json", is_flag=True, default=False, help="Print raw JSON."
)
@click.pass_context
def dynamic_frontend_delete(
    ctx: click.Context, space_id: str, output_json: bool
) -> None:
    """Delete a deployed Dynamic Frontend space by its space id.

    \b
    Example:
      unique-cli dynamic-frontend delete assistant_123
    """
    output = cmd_dynamic_frontend_delete(
        LazyState.get(ctx), space_id, output_json=output_json
    )
    click.echo(output)
    if output.startswith(_DYNAMIC_FRONTEND_ERROR_PREFIX):
        ctx.exit(1)


@main.command()
@click.argument("name_or_id")
@click.pass_context
def rm(ctx: click.Context, name_or_id: str) -> None:
    """Delete a file by path, name, or content ID.

    \b
    NAME_OR_ID is a file path, a file name matched in the current
    directory, or a content ID (cont_...).

    \b
    Examples:
      unique-cli rm report.pdf
      unique-cli rm /Reports/Q1/report.pdf
      unique-cli rm cont_abc123
    """
    output = cmd_rm(LazyState.get(ctx), name_or_id)
    emit(output)


@main.command()
@click.argument("old_name")
@click.argument("new_name")
@click.pass_context
def mv(ctx: click.Context, old_name: str, new_name: str) -> None:
    """Rename a file.

    \b
    Changes the file's display title without changing its content ID
    or location. OLD_NAME can be a file path, file name, or content ID.

    \b
    Examples:
      unique-cli mv annual.pdf annual-2025.pdf
      unique-cli mv /Reports/Q1/annual.pdf annual-2025.pdf
      unique-cli mv cont_abc123 "New Title.pdf"
    """
    output = cmd_mv_file(LazyState.get(ctx), old_name, new_name)
    emit(output)


@main.command()
@click.argument("query")
@click.option(
    "--folder",
    "-f",
    default=None,
    help=(
        "Restrict search to a folder (path, name, or scope ID). Without an "
        "active task scope, defaults to the current directory; with one, the "
        "task scope is the boundary and --folder ANDs an extra constraint."
    ),
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
    Without an active task scope, searches within the current directory
    scope with up to 200 results; use --folder to target a different
    folder. When the task defines a per-message scope, that scope is the
    search boundary regardless of the current directory, and --folder
    ANDs an additional constraint. Use --metadata to filter by custom
    metadata fields.

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

    output = cmd_search(
        state, query, folder=folder, metadata=parsed_metadata, limit=limit
    )
    click.echo(output)
    if _is_search_error_output(output):
        ctx.exit(1)


@main.command(name="uploaded-search")
@click.argument("query")
@click.option(
    "--limit",
    "-l",
    default=200,
    show_default=True,
    help="Maximum number of results to return.",
)
@click.pass_context
def uploaded_search(
    ctx: click.Context,
    query: str,
    limit: int,
) -> None:
    """Search the documents uploaded for this task (not the knowledge base).

    \b
    QUERY is the search text. This searches only the files attached to this
    row/task (e.g. an Agentic Table row's uploaded documents), which are NOT
    part of the knowledge-base folder scope and therefore never appear in
    `unique-cli search`. Results are ranked the same way and cite as
    `[sourceN]`, with numbering continuous across `search` and
    `uploaded-search` within a turn.

    \b
    Examples:
      unique-cli uploaded-search "target asset classes"
      unique-cli uploaded-search "fee structure" --limit 50
    """
    state = LazyState.get(ctx)
    output = cmd_uploaded_search(state, query, limit=limit)
    click.echo(output)
    if _is_uploaded_search_error_output(output):
        ctx.exit(1)


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
    default=None,
    help=(
        "Message ID for the MCP tool call context. Defaults to the "
        "current turn identity file ($UNIQUE_TURN_IDENTITY_FILE), then "
        "$UNIQUE_MESSAGE_ID."
    ),
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
    message_id: str | None,
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
    conversation context. When --message-id is omitted, the CLI resolves
    it from $UNIQUE_TURN_IDENTITY_FILE (preferred) or $UNIQUE_MESSAGE_ID.

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
    resolved_message_id = _resolve_cli_message_id(ctx, message_id, required=True)
    click.echo(
        cmd_mcp(
            LazyState.get(ctx),
            chat_id=chat_id,
            message_id=resolved_message_id or "",
            payload=payload,
            file=file_path,
            stdin=use_stdin,
        )
    )


@main.command()
@click.argument("tool_name")
@click.argument("message")
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to .unique-subagents.json. Defaults to $UNIQUE_SUBAGENTS_CONFIG or cwd.",
)
@click.option(
    "--chat-id",
    "parent_chat_id",
    default=None,
    envvar="UNIQUE_CHAT_ID",
    help="Parent chat ID for message correlation.",
)
@click.option(
    "--message-id",
    "parent_message_id",
    default=None,
    help=(
        "Parent message ID for message correlation. Defaults to the "
        "current turn identity file ($UNIQUE_TURN_IDENTITY_FILE), then "
        "$UNIQUE_MESSAGE_ID."
    ),
)
@click.option(
    "--assistant-id",
    "parent_assistant_id",
    default=None,
    envvar="UNIQUE_ASSISTANT_ID",
    help="Parent assistant ID for message correlation.",
)
@click.option(
    "--reset-chat",
    is_flag=True,
    help="Ignore any saved reusable chat for this subagent call.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Print the raw response JSON instead of a human-readable response.",
)
@click.pass_context
def subagent(
    ctx: click.Context,
    tool_name: str,
    message: str,
    config_path: str | None,
    parent_chat_id: str | None,
    parent_message_id: str | None,
    parent_assistant_id: str | None,
    reset_chat: bool,
    output_json: bool,
) -> None:
    """Invoke a configured connected-space subagent.

    \b
    TOOL_NAME must match an entry in .unique-subagents.json. The command sends
    MESSAGE to that connected assistant and waits for the assistant response.

    \b
    Examples:
      unique-cli subagent LegalReview "Review this contract clause"
      unique-cli subagent Finance "Summarize Q4 revenue" --reset-chat
    """
    resolved_message_id = _resolve_cli_message_id(ctx, parent_message_id)
    output = cmd_subagent(
        LazyState.get(ctx),
        tool_name=tool_name,
        message=message,
        config_path=config_path,
        parent_chat_id=parent_chat_id,
        parent_message_id=resolved_message_id,
        parent_assistant_id=parent_assistant_id,
        reset_chat=reset_chat,
        output_json=output_json,
    )
    click.echo(output)
    if _is_subagent_error_output(output):
        ctx.exit(1)


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


# -- Elicitations ----------------------------------------------------------


@main.group()
def elicit() -> None:
    """Ask the user questions via the Unique elicitation API.

    \b
    Elicitations are structured user-input requests displayed in the
    Unique UI. Use this when an agent or tool needs the user to answer
    a clarifying question, confirm a destructive action, or fill in a
    form -- instead of guessing or halting the task.

    \b
    Subcommands:
      ask       Create a form question and wait synchronously for the answer
      create    Low-level: create a FORM or URL elicitation
      pending   List pending elicitations for the current user
      get       Show details of a single elicitation by ID
      respond   Respond to an elicitation (ACCEPT / DECLINE / CANCEL / REJECT)
      wait      Poll an elicitation until it reaches a terminal state
    """


@elicit.command(name="ask")
@click.argument("message")
@click.option(
    "--tool-name",
    "-t",
    default="agent_question",
    show_default=True,
    help="Name of the tool/agent asking the question (appears in the UI).",
)
@click.option(
    "--schema",
    default=None,
    help=(
        "JSON schema for the form. Defaults to a single required "
        '"answer" string field when omitted.'
    ),
)
@click.option("--chat-id", "-c", default=None, help="Associated chat ID.")
@click.option(
    "--message-id",
    "-m",
    default=None,
    help=(
        "Associated message ID. Defaults to the current turn identity "
        "file ($UNIQUE_TURN_IDENTITY_FILE), then $UNIQUE_MESSAGE_ID."
    ),
)
@click.option(
    "--timeout",
    type=int,
    default=DEFAULT_WAIT_TIMEOUT_SECONDS,
    show_default=True,
    help=(
        "Max seconds to block waiting for the user's response. This also "
        "sets when the elicitation expires, so the request expires exactly "
        "when we stop waiting and the chat UI can offer a way to continue."
    ),
)
@click.option(
    "--poll-interval",
    type=float,
    default=2.0,
    show_default=True,
    help="Seconds between polls while waiting.",
)
@click.option(
    "--metadata",
    multiple=True,
    help="Metadata key=value pairs (repeatable).",
)
@click.option(
    "--visible/--no-visible",
    "visible",
    default=True,
    show_default=True,
    help=(
        "Wrap the elicitation in a placeholder 'thinking' timeline so the "
        "chat UI renders it (UN-19815 workaround). Requires --chat-id; the "
        "placeholder is collapsed or deleted automatically after the user "
        "responds."
    ),
)
@click.option(
    "--assistant-id",
    default=None,
    help=(
        "Assistant id to use when creating the visibility placeholder. "
        "Defaults to $UNIQUE_ASSISTANT_ID, else the latest assistant in the "
        "chat."
    ),
)
@click.option(
    "--placeholder-text",
    default=None,
    help="Text shown on the placeholder 'thinking' step while waiting.",
)
@click.option(
    "--cleanup",
    "cleanup_mode",
    type=click.Choice(["collapse", "delete"], case_sensitive=False),
    default=None,
    help=(
        "How to tear down the visibility placeholder after the user "
        "responds. 'collapse' (default) sets completedAt + a short note; "
        "'delete' removes the placeholder message entirely."
    ),
)
@click.pass_context
def elicit_ask(
    ctx: click.Context,
    message: str,
    tool_name: str,
    schema: str | None,
    chat_id: str | None,
    message_id: str | None,
    timeout: int,
    poll_interval: float,
    metadata: tuple[str, ...],
    visible: bool = True,
    assistant_id: str | None = None,
    placeholder_text: str | None = None,
    cleanup_mode: str | None = None,
) -> None:
    """Ask the user a question and wait for the answer.

    \b
    Creates a FORM elicitation in the Unique UI with the given MESSAGE
    and blocks until the user responds, the elicitation is declined /
    cancelled / expired, or --timeout is reached.

    \b
    Examples:
      unique-cli elicit ask "Which report should I send? (Q1 or Q2)"
      unique-cli elicit ask "Confirm deletion of /Archive" --timeout 60
      unique-cli elicit ask "Pick a region" \\
        --schema '{"type":"object","properties":{"region":{"type":"string","enum":["EU","US","APAC"]}},"required":["region"]}'
    """
    parsed_metadata: list[tuple[str, str]] = []
    for kv in metadata:
        if "=" not in kv:
            click.echo(f"Invalid metadata format: {kv} (expected key=value)")
            return
        k, v = kv.split("=", 1)
        parsed_metadata.append((k, v))

    ask_kwargs: dict[str, Any] = {
        "message": message,
        "tool_name": tool_name,
        "schema": schema,
        "chat_id": chat_id,
        "message_id": _resolve_cli_message_id(ctx, message_id),
        "timeout": timeout,
        "poll_interval": poll_interval,
        "metadata": parsed_metadata or None,
        "visible": visible,
        "assistant_id": assistant_id,
    }
    if placeholder_text is not None:
        ask_kwargs["placeholder_text"] = placeholder_text
    if cleanup_mode is not None:
        ask_kwargs["cleanup_mode"] = cleanup_mode.lower()
    click.echo(cmd_elicit_ask(LazyState.get(ctx), **ask_kwargs))


@elicit.command(name="create")
@click.argument("message")
@click.option(
    "--mode",
    type=click.Choice(["FORM", "URL"], case_sensitive=False),
    required=True,
    help="Elicitation display mode.",
)
@click.option(
    "--tool-name",
    "-t",
    required=True,
    help="Name of the tool/agent requesting input.",
)
@click.option(
    "--schema",
    default=None,
    help="JSON schema (required for --mode FORM).",
)
@click.option("--url", default=None, help="External URL (required for --mode URL).")
@click.option("--chat-id", "-c", default=None, help="Associated chat ID.")
@click.option(
    "--message-id",
    "-m",
    default=None,
    help=(
        "Associated message ID. Defaults to the current turn identity "
        "file ($UNIQUE_TURN_IDENTITY_FILE), then $UNIQUE_MESSAGE_ID."
    ),
)
@click.option(
    "--expires-in",
    "expires_in_seconds",
    type=int,
    default=None,
    help="Expire the elicitation after N seconds.",
)
@click.option(
    "--external-id",
    "external_elicitation_id",
    default=None,
    help="External identifier for de-duplication / tracking.",
)
@click.option(
    "--metadata",
    multiple=True,
    help="Metadata key=value pairs (repeatable).",
)
@click.option(
    "--visible/--no-visible",
    "visible",
    default=True,
    show_default=True,
    help=(
        "Wrap the elicitation in a placeholder 'thinking' timeline so the "
        "chat UI renders it (UN-19815 workaround). Requires --chat-id; the "
        "placeholder is collapsed or deleted automatically when the user "
        "responds or when you call `elicit wait` on the returned id."
    ),
)
@click.option(
    "--assistant-id",
    default=None,
    help=(
        "Assistant id to use when creating the visibility placeholder. "
        "Defaults to $UNIQUE_ASSISTANT_ID, else the latest assistant in the "
        "chat."
    ),
)
@click.option(
    "--placeholder-text",
    default=None,
    help="Text shown on the placeholder 'thinking' step while pending.",
)
@click.option(
    "--cleanup",
    "cleanup_mode",
    type=click.Choice(["collapse", "delete"], case_sensitive=False),
    default=None,
    help=(
        "How to tear down the visibility placeholder after the user "
        "responds. 'collapse' (default) sets completedAt + a short note; "
        "'delete' removes the placeholder message entirely."
    ),
)
@click.pass_context
def elicit_create(
    ctx: click.Context,
    message: str,
    mode: str,
    tool_name: str,
    schema: str | None,
    url: str | None,
    chat_id: str | None,
    message_id: str | None,
    expires_in_seconds: int | None,
    external_elicitation_id: str | None,
    metadata: tuple[str, ...],
    visible: bool = True,
    assistant_id: str | None = None,
    placeholder_text: str | None = None,
    cleanup_mode: str | None = None,
) -> None:
    """Create an elicitation without waiting for the response.

    \b
    Use this when you want to fire-and-forget, then poll later with
    `elicit wait <id>` or `elicit get <id>`. For interactive question /
    answer flows prefer `elicit ask` which does both in one call.

    \b
    Examples:
      unique-cli elicit create "Please provide feedback" \\
        --mode FORM --tool-name feedback \\
        --schema '{"type":"object","properties":{"rating":{"type":"integer"}},"required":["rating"]}'

      unique-cli elicit create "Complete the survey" \\
        --mode URL --tool-name survey --url https://example.com/s/123
    """
    parsed_metadata: list[tuple[str, str]] = []
    for kv in metadata:
        if "=" not in kv:
            click.echo(f"Invalid metadata format: {kv} (expected key=value)")
            return
        k, v = kv.split("=", 1)
        parsed_metadata.append((k, v))

    create_kwargs: dict[str, Any] = {
        "mode": mode,
        "message": message,
        "tool_name": tool_name,
        "schema": schema,
        "url": url,
        "chat_id": chat_id,
        "message_id": _resolve_cli_message_id(ctx, message_id),
        "expires_in_seconds": expires_in_seconds,
        "external_elicitation_id": external_elicitation_id,
        "metadata": parsed_metadata or None,
        "visible": visible,
        "assistant_id": assistant_id,
    }
    if placeholder_text is not None:
        create_kwargs["placeholder_text"] = placeholder_text
    if cleanup_mode is not None:
        create_kwargs["cleanup_mode"] = cleanup_mode.lower()
    click.echo(cmd_elicit_create(LazyState.get(ctx), **create_kwargs))


@elicit.command(name="pending")
@click.pass_context
def elicit_pending(ctx: click.Context) -> None:
    """List all pending elicitations for the current user.

    \b
    Examples:
      unique-cli elicit pending
    """
    click.echo(cmd_elicit_pending(LazyState.get(ctx)))


@elicit.command(name="get")
@click.argument("elicitation_id")
@click.pass_context
def elicit_get(ctx: click.Context, elicitation_id: str) -> None:
    """Show details of a single elicitation by ID.

    \b
    Examples:
      unique-cli elicit get elicit_abc123
    """
    click.echo(cmd_elicit_get(LazyState.get(ctx), elicitation_id))


@elicit.command(name="wait")
@click.argument("elicitation_id")
@click.option(
    "--timeout",
    type=int,
    default=DEFAULT_WAIT_TIMEOUT_SECONDS,
    show_default=True,
    help="Max seconds to wait for a terminal state.",
)
@click.option(
    "--poll-interval",
    type=float,
    default=2.0,
    show_default=True,
    help="Seconds between polls.",
)
@click.pass_context
def elicit_wait(
    ctx: click.Context,
    elicitation_id: str,
    timeout: int,
    poll_interval: float,
) -> None:
    """Poll an elicitation until it is answered, declined, cancelled, or expires.

    \b
    Examples:
      unique-cli elicit wait elicit_abc123
      unique-cli elicit wait elicit_abc123 --timeout 60 --poll-interval 1
    """
    click.echo(
        cmd_elicit_wait(
            LazyState.get(ctx),
            elicitation_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    )


@elicit.command(name="respond")
@click.argument("elicitation_id")
@click.option(
    "--action",
    type=click.Choice(["ACCEPT", "DECLINE", "CANCEL", "REJECT"], case_sensitive=False),
    required=True,
    help="Response action.",
)
@click.option(
    "--content",
    default=None,
    help="JSON object with response fields (required for ACCEPT).",
)
@click.pass_context
def elicit_respond(
    ctx: click.Context,
    elicitation_id: str,
    action: str,
    content: str | None,
) -> None:
    """Respond to an elicitation (mostly for scripting / testing).

    \b
    The user normally answers via the Unique UI. Use this to script
    declines / cancels, or to simulate a user response in tests.

    \b
    Examples:
      unique-cli elicit respond elicit_abc123 --action ACCEPT \\
        --content '{"answer":"yes"}'
      unique-cli elicit respond elicit_abc123 --action DECLINE
      unique-cli elicit respond elicit_abc123 --action CANCEL
    """
    click.echo(
        cmd_elicit_respond(
            LazyState.get(ctx),
            elicitation_id,
            action=action,
            content=content,
        )
    )


# -- Browser Steering ------------------------------------------------------


_BROWSER_HELP = """\
Steer the user's live, signed-in Chrome tab via the Unique browser extension.

\b
Commands talk to the browser-bridge relay, which forwards each action to the
extension over the user's outbound WebSocket. You never see the page directly —
work from the DOM snapshot `get-dom` returns.

\b
Core loop:
  1. read   unique-cli browser get-dom          (pruned a11y tree + `ref`s)
  2. act    unique-cli browser click --ref e42   (use a ref from the latest DOM)
  3. re-read after anything that changes the page; refs are per-snapshot only.

\b
Every subcommand prints a JSON envelope: {"ok": true, "result": ...} or
{"ok": false, "error": "<code>", ...}. On `browser_not_connected`, relay the
remediation to the user and stop until the extension is installed and signed in.

\b
Examples:
  unique-cli browser status
  unique-cli browser get-dom
  unique-cli browser navigate --url https://example.com
  unique-cli browser click --ref e42
  unique-cli browser fill --ref e10 --text "hello@unique.ch"
  unique-cli browser download "https://portal/report.pdf" ./output/report.pdf
"""


def _browser_target_args(ref: str | None, selector: str | None) -> dict[str, Any]:
    """Build the {ref|selector} arg map, preferring an explicit ref.

    Empty strings are treated as absent so ``--ref ""`` / ``--selector ""``
    cannot bypass the missing-target guard and reach the bridge.
    """
    args: dict[str, Any] = {}
    if ref:
        args["ref"] = ref
    if selector:
        args["selector"] = selector
    return args


def _browser_missing_target(verb: str) -> str:
    """JSON error envelope for a verb invoked without --ref or --selector."""
    return json.dumps(
        {
            "ok": False,
            "error": "browser_missing_target",
            "message": f"{verb} requires --ref (from the latest get-dom) or --selector.",
        },
        indent=2,
    )


def _browser_missing_condition(verb: str, required: str) -> str:
    """JSON error envelope for a verb invoked without a required condition."""
    return json.dumps(
        {
            "ok": False,
            "error": "browser_missing_target",
            "message": f"{verb} requires {required}.",
        },
        indent=2,
    )


@main.group(help=_BROWSER_HELP)
def browser() -> None:
    pass


@browser.command(name="status")
@click.pass_context
def browser_status(ctx: click.Context) -> None:
    """Check whether a browser extension is connected for this user."""
    emit(cmd_browser_status(LazyState.get(ctx)), is_error=_is_browser_error_output)


@browser.command(name="get-dom")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_get_dom(ctx: click.Context, tab_id: int | None) -> None:
    """Return a pruned accessibility tree with `ref` handles for the active tab."""
    emit(
        cmd_browser_action(LazyState.get(ctx), "get-dom", {}, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="screenshot")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_screenshot(ctx: click.Context, tab_id: int | None) -> None:
    """Capture a PNG of the visible tab (returned as a data URL). Costs tokens."""
    emit(
        cmd_browser_action(LazyState.get(ctx), "screenshot", {}, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="navigate")
@click.option("--url", required=True, help="URL to load in the active tab.")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_navigate(ctx: click.Context, url: str, tab_id: int | None) -> None:
    """Load a URL in the active tab and wait for load."""
    emit(
        cmd_browser_action(LazyState.get(ctx), "navigate", {"url": url}, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="click")
@click.option("--ref", default=None, help="Element ref from the latest get-dom.")
@click.option("--selector", default=None, help="CSS selector (fallback when no ref).")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_click(
    ctx: click.Context, ref: str | None, selector: str | None, tab_id: int | None
) -> None:
    """Click an element by `--ref` (preferred) or `--selector`."""
    if not ref and not selector:
        emit(
            _browser_missing_target("click"),
            is_error=_is_browser_error_output,
        )
        return
    args = _browser_target_args(ref, selector)
    emit(
        cmd_browser_action(LazyState.get(ctx), "click", args, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="type")
@click.option("--text", required=True, help="Text to append into the field.")
@click.option("--ref", default=None, help="Element ref from the latest get-dom.")
@click.option("--selector", default=None, help="CSS selector (fallback when no ref).")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_type(
    ctx: click.Context,
    text: str,
    ref: str | None,
    selector: str | None,
    tab_id: int | None,
) -> None:
    """Append text into a field (does not clear existing value; see `fill`)."""
    if not ref and not selector:
        emit(_browser_missing_target("type"), is_error=_is_browser_error_output)
        return
    args = _browser_target_args(ref, selector)
    args["text"] = text
    emit(
        cmd_browser_action(LazyState.get(ctx), "type", args, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="fill")
@click.option("--text", required=True, help="Replacement value for the field.")
@click.option("--ref", default=None, help="Element ref from the latest get-dom.")
@click.option("--selector", default=None, help="CSS selector (fallback when no ref).")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_fill(
    ctx: click.Context,
    text: str,
    ref: str | None,
    selector: str | None,
    tab_id: int | None,
) -> None:
    """Replace a field's entire value."""
    if not ref and not selector:
        emit(_browser_missing_target("fill"), is_error=_is_browser_error_output)
        return
    args = _browser_target_args(ref, selector)
    args["text"] = text
    emit(
        cmd_browser_action(LazyState.get(ctx), "fill", args, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="select")
@click.option("--value", required=True, help="Option value to select.")
@click.option("--ref", default=None, help="Element ref from the latest get-dom.")
@click.option("--selector", default=None, help="CSS selector (fallback when no ref).")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_select(
    ctx: click.Context,
    value: str,
    ref: str | None,
    selector: str | None,
    tab_id: int | None,
) -> None:
    """Choose a `<select>` option by value."""
    if not ref and not selector:
        emit(_browser_missing_target("select"), is_error=_is_browser_error_output)
        return
    args = _browser_target_args(ref, selector)
    args["value"] = value
    emit(
        cmd_browser_action(LazyState.get(ctx), "select", args, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="press")
@click.option("--key", required=True, help="Key to send, e.g. Enter, Tab, Escape.")
@click.option("--ref", default=None, help="Focus this element first (optional).")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_press(
    ctx: click.Context, key: str, ref: str | None, tab_id: int | None
) -> None:
    """Send a key event (optionally after focusing `--ref`)."""
    args: dict[str, Any] = {"key": key}
    if ref:
        args["ref"] = ref
    emit(
        cmd_browser_action(LazyState.get(ctx), "press", args, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="scroll")
@click.option("--ref", default=None, help="Scroll this element into view (optional).")
@click.option(
    "--y", type=int, default=None, help="Absolute vertical scroll position (px)."
)
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_scroll(
    ctx: click.Context, ref: str | None, y: int | None, tab_id: int | None
) -> None:
    """Scroll the page, or to a specific element / y offset."""
    args: dict[str, Any] = {}
    if ref:
        args["ref"] = ref
    if y is not None:
        args["y"] = y
    emit(
        cmd_browser_action(LazyState.get(ctx), "scroll", args, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="wait-for")
@click.option(
    "--selector", default=None, help="Wait until this CSS selector is present."
)
@click.option("--text", default=None, help="Wait until this text appears on the page.")
@click.option("--timeout-ms", type=int, default=None, help="Max wait in milliseconds.")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_wait_for(
    ctx: click.Context,
    selector: str | None,
    text: str | None,
    timeout_ms: int | None,
    tab_id: int | None,
) -> None:
    """Wait for a selector or text to appear before continuing."""
    if not selector and not text:
        emit(
            _browser_missing_condition("wait-for", "--selector or --text"),
            is_error=_is_browser_error_output,
        )
        return
    args: dict[str, Any] = {}
    if selector:
        args["selector"] = selector
    if text:
        args["text"] = text
    if timeout_ms is not None:
        args["timeoutMs"] = timeout_ms
    emit(
        cmd_browser_action(LazyState.get(ctx), "wait-for", args, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="list-tabs")
@click.pass_context
def browser_list_tabs(ctx: click.Context) -> None:
    """List open tabs (tabId, title, url)."""
    emit(
        cmd_browser_action(LazyState.get(ctx), "list-tabs", {}),
        is_error=_is_browser_error_output,
    )


@browser.command(name="open-tab")
@click.option("--url", required=True, help="URL to open in a new tab.")
@click.pass_context
def browser_open_tab(ctx: click.Context, url: str) -> None:
    """Open a new tab at the given URL."""
    emit(
        cmd_browser_action(LazyState.get(ctx), "open-tab", {"url": url}),
        is_error=_is_browser_error_output,
    )


@browser.command(name="extract-links")
@click.option(
    "--tab-id", type=int, default=None, help="Target tab id (default: active tab)."
)
@click.pass_context
def browser_extract_links(ctx: click.Context, tab_id: int | None) -> None:
    """Return all visible links on the active tab."""
    emit(
        cmd_browser_action(LazyState.get(ctx), "extract-links", {}, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="download")
@click.argument("url")
@click.argument("dest")
@click.option("--tab-id", type=int, default=None, help="Tab whose session to use.")
@click.pass_context
def browser_download(
    ctx: click.Context, url: str, dest: str, tab_id: int | None
) -> None:
    """Download URL using the page session and save it to workspace path DEST.

    \b
    Fetches the resource with the tab's existing login/session (essential for
    files behind a sign-in) and writes the bytes to DEST. It does NOT upload to
    the knowledge base or attach to the chat — do that as a separate follow-up
    (e.g. `unique-cli upload <file> <folder>`).

    \b
    Examples:
      unique-cli browser download "https://portal/report.pdf" ./output/report.pdf
    """
    emit(
        cmd_browser_download(LazyState.get(ctx), url, dest, tab_id=tab_id),
        is_error=_is_browser_error_output,
    )


@browser.command(name="open-panel")
@click.pass_context
def browser_open_panel(ctx: click.Context) -> None:
    """Open the Unique side panel in the user's browser (extension shell)."""
    emit(
        cmd_browser_control(LazyState.get(ctx), "open-panel", {}),
        is_error=_is_browser_error_output,
    )


@browser.command(name="focus-tab")
@click.option(
    "--tab-id", type=int, required=True, help="Tab id to bring to the foreground."
)
@click.pass_context
def browser_focus_tab(ctx: click.Context, tab_id: int) -> None:
    """Bring a specific tab to the foreground (extension shell control)."""
    emit(
        cmd_browser_control(LazyState.get(ctx), "focus-tab", {"tabId": tab_id}),
        is_error=_is_browser_error_output,
    )


# -- Web Search ------------------------------------------------------------


# Key under which the `web-search` group stashes its `--config` path on
# `ctx.meta`, so subcommands can read it back via
# ``_resolve_web_search_config_path``. Kept as a module-level constant so the
# writer (group) and reader (subcommand helper) cannot drift.
_WEB_SEARCH_GROUP_CONFIG_KEY = "web_search_config_path"


@main.group("web-search")
@click.version_option(version=__version__, prog_name="unique-cli web-search")
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(),
    help=(
        "Path to a JSON config file (full WebSearchConfig payload or "
        "simple {search_engine_config: {...}, crawler_config: {...}} "
        f"overrides). Falls back to ${ENV_CONFIG_PATH} and then "
        "~/.unique-websearch.json."
    ),
)
@click.pass_context
def web_search_group(ctx: click.Context, config_path: str | None) -> None:
    """Two-phase web search through the Unique public API.

    \b
    Phase 1 -- search:  query a search engine, get back URLs and snippets.
    Phase 2 -- crawl:   fetch full page content for selected URLs.

    \b
    Engine and crawler are resolved server-side from
    ACTIVE_SEARCH_ENGINES / ACTIVE_INHOUSE_CRAWLERS, matching the
    server's WebSearchConfig defaults. Per-call overrides use the
    same JSON shapes the assistants-core service expects, and can be
    supplied via --config (file), inline --engine-config /
    --crawler-config (JSON), or the equivalent flags on each subcommand.

    \b
    Override precedence (highest first):
      1. Inline --fetch-size / --engine-config / --crawler-config flags
      2. Config file (--config / $UNIQUE_WEBSEARCH_CONFIG / ~/.unique-websearch.json)
      3. Server-side defaults

    \b
    Subcommands:
      search    Run a web search and print URLs + snippets
      crawl     Crawl a list of URLs and print their content
    """
    if config_path is not None:
        ctx.meta[_WEB_SEARCH_GROUP_CONFIG_KEY] = config_path


def _resolve_web_search_config_path(
    ctx: click.Context, subcommand_value: str | None
) -> str | None:
    """Subcommand value wins; otherwise fall back to the group's --config."""
    if subcommand_value is not None:
        return subcommand_value
    return ctx.meta.get(_WEB_SEARCH_GROUP_CONFIG_KEY)


def _emit_web_search(ctx: click.Context, output: str) -> None:
    """Echo a cmd_web_* result and translate error strings to exit code 1."""
    click.echo(output)
    if _is_web_search_error_output(output):
        ctx.exit(1)


_SEARCH_HELP = """\
Run a web search via /web-search-api/search.

\b
Examples:
  unique-cli web-search search "quarterly earnings 2026"
  unique-cli web-search search "AI regulation" -n 10
  unique-cli web-search search "python tutorial" --json
  unique-cli web-search search "sustainability" --include-content --json
  unique-cli web-search search "tax reform" \\
    --engine-config '{"searchEngineName":"Google","fetchSize":3}'
  unique-cli web-search --config ./ws.json search "EU AI act"
"""


@web_search_group.command("search", help=_SEARCH_HELP)
@click.argument("query")
@click.option(
    "--fetch-size",
    "-n",
    default=None,
    type=int,
    help="Override the engine's fetchSize (number of results to fetch).",
)
@click.option(
    "--include-content",
    "-i",
    is_flag=True,
    default=False,
    help="Populate result.content via the configured crawler when the engine requires scraping.",
)
@click.option(
    "--engine-config",
    "engine_config_raw",
    default=None,
    help='Override the searchEngineConfig as a JSON object (e.g. \'{"searchEngineName":"Google"}\').',
)
@click.option(
    "--crawler-config",
    "crawler_config_raw",
    default=None,
    help="Override the crawlerConfig as a JSON object (only used with --include-content).",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(),
    help="Per-call override of the web-search group's --config path.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON (suitable for piping into web-search crawl --stdin).",
)
@click.option(
    "--chat-id",
    "chat_id",
    default=None,
    envvar="UNIQUE_CHAT_ID",
    help=(
        "Chat id this call is made on behalf of. Defaults to $UNIQUE_CHAT_ID "
        "(auto-set in Conduct sandboxes). When set, the space's Web Search "
        "toggle is enforced server-side and the call is rejected if Web "
        "Search is disabled for that space."
    ),
)
@click.pass_context
def web_search_search_cmd(
    ctx: click.Context,
    query: str,
    fetch_size: int | None,
    include_content: bool,
    engine_config_raw: str | None,
    crawler_config_raw: str | None,
    config_path: str | None,
    output_json: bool,
    chat_id: str | None,
) -> None:
    """Search the web via the Unique public API."""
    resolved_config = _resolve_web_search_config_path(ctx, config_path)
    output = cmd_web_search(
        LazyState.get(ctx),
        query,
        fetch_size=fetch_size,
        include_content=include_content,
        engine_config_raw=engine_config_raw,
        crawler_config_raw=crawler_config_raw,
        output_json=output_json,
        config_path=resolved_config,
        chat_id=chat_id,
    )
    _emit_web_search(ctx, output)


_CRAWL_HELP = """\
Crawl a list of URLs via /web-search-api/crawl.

URLs can be passed as positional arguments or piped via stdin (one per line).

\b
Examples:
  unique-cli web-search crawl https://example.com https://other.com
  unique-cli web-search crawl --parallel 5 https://a.com https://b.com
  echo "https://example.com" | unique-cli web-search crawl --stdin
  unique-cli web-search search "query" --json | jq -r '.results[].url' \\
    | unique-cli web-search crawl --stdin
"""


@web_search_group.command("crawl", help=_CRAWL_HELP)
@click.argument("urls", nargs=-1)
@click.option(
    "--parallel",
    "-p",
    default=10,
    type=click.IntRange(min=1),
    show_default=True,
    help="Number of URLs the server crawls concurrently per batch.",
)
@click.option(
    "--stdin",
    "from_stdin",
    is_flag=True,
    help="Read URLs from stdin (one per line).",
)
@click.option(
    "--crawler-config",
    "crawler_config_raw",
    default=None,
    help='Override the crawlerConfig as a JSON object (e.g. \'{"crawlerType":"BasicCrawler"}\').',
)
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(),
    help="Per-call override of the web-search group's --config path.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON.",
)
@click.option(
    "--chat-id",
    "chat_id",
    default=None,
    envvar="UNIQUE_CHAT_ID",
    help=(
        "Chat id this call is made on behalf of. Defaults to $UNIQUE_CHAT_ID "
        "(auto-set in Conduct sandboxes). When set, the space's Web Search "
        "toggle is enforced server-side and the call is rejected if Web "
        "Search is disabled for that space."
    ),
)
@click.pass_context
def web_search_crawl_cmd(
    ctx: click.Context,
    urls: tuple[str, ...],
    parallel: int,
    from_stdin: bool,
    crawler_config_raw: str | None,
    config_path: str | None,
    output_json: bool,
    chat_id: str | None,
) -> None:
    """Crawl URLs via the Unique public API."""
    url_list: list[str] = list(urls)
    if from_stdin:
        stdin_urls = [
            line.strip() for line in click.get_text_stream("stdin") if line.strip()
        ]
        url_list.extend(stdin_urls)

    resolved_config = _resolve_web_search_config_path(ctx, config_path)
    output = cmd_web_crawl(
        LazyState.get(ctx),
        url_list,
        parallel=parallel,
        crawler_config_raw=crawler_config_raw,
        output_json=output_json,
        config_path=resolved_config,
        chat_id=chat_id,
    )
    _emit_web_search(ctx, output)
