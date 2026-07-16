"""Chat sub-app — send messages and inspect history."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from uqadm.chat.history import cmd_history
from uqadm.chat.send import cmd_send

chat_app = typer.Typer(
    name="chat",
    help="Chat with an assistant or inspect chat history.",
    no_args_is_help=True,
)

_STOP_ON_VALUES = {"stoppedStreamingAt", "completedAt"}
_SLOT_HELP = (
    "Credential slot (loads .{SLOT}.env). "
    "Omit to use the configured default (see `uqadm env set-default`). "
    "Ignored when UQADM_AUTH_FROM_ENV is set — credentials are read from the "
    "process environment and no slot file is used."
)


def _get_cwd(ctx: typer.Context) -> Path | None:
    return (ctx.obj or {}).get("cwd")


@chat_app.command(
    "send", short_help="Send a message to an assistant and print the reply."
)
def chat_send(
    ctx: typer.Context,
    assistant_id: Annotated[
        str,
        typer.Argument(
            metavar="ASSISTANT_ID",
            help="The assistant ID to send the message to.",
        ),
    ],
    slot: Annotated[
        Optional[str],
        typer.Option("--slot", help=_SLOT_HELP),
    ] = None,
    text: Annotated[
        Optional[str],
        typer.Option("--text", help="Message text (alternative to --file or stdin)."),
    ] = None,
    file: Annotated[
        Optional[Path],
        typer.Option(
            "--file",
            help="Read message from this file (alternative to --text or stdin).",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    chat_id: Annotated[
        Optional[str],
        typer.Option("--chat-id", help="Continue an existing chat thread."),
    ] = None,
    tool_choices: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tool",
            help="Force a specific tool (repeatable: --tool web_search --tool code_interpreter).",
        ),
    ] = None,
    poll_interval: Annotated[
        float,
        typer.Option(
            "--poll-interval",
            help="Seconds between completion polls.",
            show_default=True,
        ),
    ] = 1.0,
    max_wait: Annotated[
        float,
        typer.Option(
            "--max-wait",
            help="Maximum seconds to wait for a response.",
            show_default=True,
        ),
    ] = 300.0,
    stop_on: Annotated[
        str,
        typer.Option(
            "--stop-on",
            help="Stop condition: stoppedStreamingAt or completedAt.",
            show_default=True,
        ),
    ] = "stoppedStreamingAt",
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Print the full Space.Message as JSON."),
    ] = False,
) -> None:
    """Send a prompt to an assistant and print the reply.

    The chat_id of the new (or continued) thread is printed to stderr so you
    can pass it to --chat-id in a follow-up call.

    Examples:

      uqadm chat send asst_abc123 --text "Hello"
      uqadm chat send asst_abc123 --text "Follow up" --chat-id chat_xyz
      uqadm chat send asst_abc123 --slot prod --file ./prompt.txt
      uqadm chat send asst_abc123 --text "Search this" --tool web_search
      uqadm chat send asst_abc123 --text "Run code" --tool code_interpreter --tool web_search
      echo "Summarize this" | uqadm chat send asst_abc123
    """
    if stop_on not in _STOP_ON_VALUES:
        typer.echo(
            f"--stop-on must be one of: {', '.join(sorted(_STOP_ON_VALUES))}",
            err=True,
        )
        raise typer.Exit(2)
    cmd_send(
        assistant_id,
        slot=slot,
        text=text,
        file=file,
        chat_id=chat_id,
        tool_choices=tool_choices,
        poll_interval=poll_interval,
        max_wait=max_wait,
        stop_on=stop_on,
        as_json=as_json,
        cwd=_get_cwd(ctx),
    )


@chat_app.command("history", short_help="Fetch and display chat history.")
def chat_history(
    ctx: typer.Context,
    chat_id: Annotated[
        str,
        typer.Argument(
            metavar="CHAT_ID",
            help="The chat ID to fetch history for.",
        ),
    ],
    slot: Annotated[
        Optional[str],
        typer.Option("--slot", help=_SLOT_HELP),
    ] = None,
    max_tokens: Annotated[
        int,
        typer.Option(
            "--max-tokens",
            help="Token budget for the history window.",
            show_default=True,
        ),
    ] = 8000,
    percent: Annotated[
        float,
        typer.Option(
            "--percent",
            help="Fraction of max_tokens allocated to history.",
            show_default=True,
        ),
    ] = 0.15,
    max_messages: Annotated[
        int,
        typer.Option(
            "--max-messages",
            help="Maximum number of messages to consider.",
            show_default=True,
        ),
    ] = 4,
    show_full: Annotated[
        bool,
        typer.Option(
            "--full", help="Show the full history instead of the selected window."
        ),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Print raw message structures as JSON."),
    ] = False,
) -> None:
    """Fetch chat history and display the selected token window (or full with --full).

    Examples:

      uqadm chat history chat_xyz
      uqadm chat history chat_xyz --full --json
      uqadm chat history chat_xyz --slot prod
    """
    cmd_history(
        chat_id,
        slot=slot,
        max_tokens=max_tokens,
        percent=percent,
        max_messages=max_messages,
        show_full=show_full,
        as_json=as_json,
        cwd=_get_cwd(ctx),
    )
