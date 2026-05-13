"""Shared terminal rendering helpers for chat commands."""

from __future__ import annotations

import re
import sys
from typing import Any

import typer

# Strips ANSI/OSC/DCS/SOS/PM/APC escape sequences and raw C0/C1 control bytes
# from untrusted server content before it reaches the terminal.
#
# Preserved intentionally: \t (0x09), \n (0x0a) — legitimate text content.
# \r (0x0d) is normalised away to prevent carriage-return overwrite attacks.
_CONTROL_RE = re.compile(
    r"\x1b"
    r"(?:"
    r"\[[0-9;:<=>?]*[ -/]*[@-~]"  # CSI  — SGR, cursor movement, etc.
    r"|\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC  — title, hyperlink, iTerm2, …
    r"|[PX^_][^\x1b]*(?:\x1b\\|$)"  # DCS / SOS / PM / APC
    r"|[@-~]"  # Fe/Fp two-byte sequences (ESC M, ESC c RIS, ESC 7/8, …)
    r")"
    r"|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]"  # raw C0/C1 (keep \t \n)
)


def _sanitize(value: str) -> str:
    """Strip terminal control sequences from untrusted server-supplied text."""
    cleaned = _CONTROL_RE.sub("", value)
    # Normalise \r\n → \n and lone \r → \n to prevent carriage-return overwrite.
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return cleaned


_ROLE_LABEL = {
    "user": "You",
    "assistant": "Assistant",
    "system": "System",
}


def rule() -> None:
    width = typer.get_terminal_size().columns if sys.stdout.isatty() else 60
    typer.echo("─" * width)


def _render_references(references: list[dict[str, Any]]) -> None:
    rule()
    typer.echo("References")
    for ref in sorted(references, key=lambda r: r.get("sequenceNumber", 0)):
        seq = ref.get("sequenceNumber", "?")
        name = _sanitize(ref.get("name") or ref.get("source") or "(unknown)")
        url = _sanitize(ref.get("url") or "")
        line = f"  [{seq}] {name}"
        if url:
            line += f"  {url}"
        typer.echo(line)


def _render_assessments(assessments: list[dict[str, Any]]) -> None:
    rule()
    typer.echo("Evaluation")
    for a in assessments:
        status = _sanitize(a.get("status") or "")
        label = _sanitize(a.get("label") or "")
        title = _sanitize(a.get("title") or "")
        explanation = _sanitize((a.get("explanation") or "").strip())
        header_parts = [p for p in [status, label, title] if p]
        typer.echo(f"  {' · '.join(header_parts)}" if header_parts else "")
        if explanation:
            typer.echo(f"  {explanation}")


def print_framed_message(result: dict[str, Any]) -> None:
    """Print a single assistant reply with chat_id, answer, references, evaluation."""
    chat_id = _sanitize(result.get("chatId") or result.get("chat_id") or "")
    reply_text = _sanitize((result.get("text") or "").strip())
    references: list[dict[str, Any]] = result.get("references") or []
    assessments: list[dict[str, Any]] = result.get("assessment") or []

    rule()
    typer.echo(f"chat_id: {chat_id}")
    rule()
    typer.echo(reply_text)

    if references:
        _render_references(references)
    if assessments:
        _render_assessments(assessments)

    rule()


def print_framed_history(messages: list[dict[str, Any]]) -> None:
    """Print a sequence of chat messages, each in its own framed block."""
    for msg in messages:
        raw_role = _sanitize((msg.get("role") or "unknown").lower())
        label = _ROLE_LABEL.get(raw_role, raw_role.capitalize())
        text = _sanitize((msg.get("text") or msg.get("content") or "").strip())
        references: list[dict[str, Any]] = msg.get("references") or []
        assessments: list[dict[str, Any]] = msg.get("assessment") or []

        rule()
        typer.echo(label)
        rule()
        typer.echo(text)

        if references:
            _render_references(references)
        if assessments:
            _render_assessments(assessments)

    rule()
