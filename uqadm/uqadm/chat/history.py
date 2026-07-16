"""Fetch and display chat history for a given chat ID."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from unique_sdk.utils.chat_history import load_history

from uqadm.chat.render import print_framed_history
from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.cli_auth import load_config_or_exit, resolve_slot_or_exit


def cmd_history(
    chat_id: str,
    *,
    slot: str | None,
    max_tokens: int,
    percent: float,
    max_messages: int,
    show_full: bool,
    as_json: bool,
    cwd: Path | None,
) -> None:
    """Load chat history and display the selected window."""
    resolved_slot = resolve_slot_or_exit(slot)
    cfg = load_config_or_exit(resolved_slot, cwd)

    try:
        import unique_sdk

        unique_sdk.api_key = cfg.api_key
        unique_sdk.app_id = cfg.app_id
        unique_sdk.api_base = cfg.api_base

        if show_full:
            # Message.list returns the complete untruncated conversation.
            # load_history always drops the last 2 messages (context-injection
            # behaviour) so we bypass it for --full.
            list_result = unique_sdk.Message.list(
                user_id=cfg.user_id,
                company_id=cfg.company_id,
                chatId=chat_id,
            )
            target: list[dict[str, Any]] = [dict(m) for m in list_result.data]
        else:
            _, selected_history = load_history(
                cfg.user_id,
                cfg.company_id,
                chat_id,
                max_tokens,
                percentOfMaxTokens=percent,
                maxMessages=max_messages,
            )
            target = selected_history
    except Exception as exc:
        typer.echo(f"chat history failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="chat history")
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(target, indent=2, default=str))
    else:
        print_framed_history(target)
