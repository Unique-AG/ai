"""Send a message to an assistant and wait for completion."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Literal, cast

import typer
from unique_sdk import Space
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

from uqadm.chat.render import print_framed_message
from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.env import (
    MissingEnvCredentialsError,
    MissingSlotEnvFileError,
    config_for_slot,
)
from uqadm.core.slot import MissingDefaultSlotError, resolve_slot

StopCondition = Literal["stoppedStreamingAt", "completedAt"]


def _read_message_text(
    text: str | None,
    file: Path | None,
) -> str:
    """Resolve message body: --text wins, then --file, then stdin."""
    if text is not None:
        return text
    if file is not None:
        return file.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    typer.echo(
        "Error: provide message via --text TEXT, --file PATH, or pipe to stdin.",
        err=True,
    )
    raise typer.Exit(2)


def cmd_send(
    assistant_id: str,
    *,
    slot: str | None,
    text: str | None,
    file: Path | None,
    chat_id: str | None,
    tool_choices: list[str] | None,
    poll_interval: float,
    max_wait: float,
    stop_on: str,
    as_json: bool,
    cwd: Path | None,
) -> None:
    """Send a message to an assistant and print the reply."""
    try:
        resolved_slot = resolve_slot(slot)
    except MissingDefaultSlotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)

    message_text = _read_message_text(text, file)

    try:
        cfg = config_for_slot(resolved_slot, cwd=cwd)
    except (MissingSlotEnvFileError, MissingEnvCredentialsError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)

    try:
        import unique_sdk

        unique_sdk.api_key = cfg.api_key
        unique_sdk.app_id = cfg.app_id
        unique_sdk.api_base = cfg.api_base

        result: Space.Message = asyncio.run(
            send_message_and_wait_for_completion(
                user_id=cfg.user_id,
                company_id=cfg.company_id,
                assistant_id=assistant_id,
                text=message_text,
                chat_id=chat_id,
                tool_choices=tool_choices or None,
                poll_interval=poll_interval,
                max_wait=max_wait,
                stop_condition=cast(StopCondition, stop_on),
            )
        )
    except TimeoutError:
        typer.echo(
            f"Timed out after {max_wait}s waiting for assistant response.", err=True
        )
        raise typer.Exit(1)
    except Exception as exc:
        typer.echo(f"chat send failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="chat send")
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(dict(result), indent=2, default=str))
    else:
        print_framed_message(result)
