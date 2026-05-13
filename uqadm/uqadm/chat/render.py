"""Shared terminal rendering helpers for chat commands."""

from __future__ import annotations

import sys
from typing import Any

import typer

_ROLE_LABEL = {
    "user": "You",
    "assistant": "Assistant",
    "system": "System",
}


def rule() -> None:
    width = typer.get_terminal_size().columns if sys.stdout.isatty() else 60
    typer.echo("─" * width)


def print_framed_message(result: dict[str, Any]) -> None:
    """Print a single assistant reply with chat_id, answer, references, evaluation."""
    chat_id = result.get("chatId") or result.get("chat_id") or ""
    reply_text = (result.get("text") or "").strip()
    references: list[dict[str, Any]] = result.get("references") or []
    assessments: list[dict[str, Any]] = result.get("assessment") or []

    rule()
    typer.echo(f"chat_id: {chat_id}")
    rule()
    typer.echo(reply_text)

    if references:
        rule()
        typer.echo("References")
        for ref in sorted(references, key=lambda r: r.get("sequenceNumber", 0)):
            seq = ref.get("sequenceNumber", "?")
            name = ref.get("name") or ref.get("source") or "(unknown)"
            url = ref.get("url") or ""
            line = f"  [{seq}] {name}"
            if url:
                line += f"  {url}"
            typer.echo(line)

    if assessments:
        rule()
        typer.echo("Evaluation")
        for a in assessments:
            status = a.get("status") or ""
            label = a.get("label") or ""
            title = a.get("title") or ""
            explanation = (a.get("explanation") or "").strip()
            header_parts = [p for p in [status, label, title] if p]
            typer.echo(f"  {' · '.join(header_parts)}" if header_parts else "")
            if explanation:
                typer.echo(f"  {explanation}")

    rule()


def print_framed_history(messages: list[dict[str, Any]]) -> None:
    """Print a sequence of chat messages, each in its own framed block."""
    for msg in messages:
        raw_role = (msg.get("role") or "unknown").lower()
        label = _ROLE_LABEL.get(raw_role, raw_role.capitalize())
        text = (msg.get("text") or msg.get("content") or "").strip()
        references: list[dict[str, Any]] = msg.get("references") or []
        assessments: list[dict[str, Any]] = msg.get("assessment") or []

        rule()
        typer.echo(label)
        rule()
        typer.echo(text)

        if references:
            rule()
            typer.echo("References")
            for ref in sorted(references, key=lambda r: r.get("sequenceNumber", 0)):
                seq = ref.get("sequenceNumber", "?")
                name = ref.get("name") or ref.get("source") or "(unknown)"
                url = ref.get("url") or ""
                line = f"  [{seq}] {name}"
                if url:
                    line += f"  {url}"
                typer.echo(line)

        if assessments:
            rule()
            typer.echo("Evaluation")
            for a in assessments:
                status = a.get("status") or ""
                label_text = a.get("label") or ""
                title = a.get("title") or ""
                explanation = (a.get("explanation") or "").strip()
                header_parts = [p for p in [status, label_text, title] if p]
                typer.echo(f"  {' · '.join(header_parts)}" if header_parts else "")
                if explanation:
                    typer.echo(f"  {explanation}")

    rule()
