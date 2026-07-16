"""Compare two space payloads with editor-style views and sensible defaults."""

from __future__ import annotations

import json
import sys
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any, Literal

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from unique_sdk import Space

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.cli_auth import load_config_or_exit
from uqadm.core.endpoint import EndpointParseError, parse_source_endpoint

# Stripped in the default (non-strict) mode so diffs focus on meaningful config drift.
_NORMALIZE_KEYS = frozenset(
    {
        "createdAt",
        "updatedAt",
        "id",
        "moduleId",
        "companyId",
        "createdBy",
        "updatedBy",
    }
)

DiffFormat = Literal["unified", "side-by-side"]


def _normalize_for_diff(obj: Any, *, strict: bool) -> Any:
    """Drop ephemeral keys recursively unless ``strict``."""
    if strict:
        return obj
    if isinstance(obj, dict):
        return {
            k: _normalize_for_diff(v, strict=strict)
            for k, v in obj.items()
            if k not in _NORMALIZE_KEYS
        }
    if isinstance(obj, list):
        return [_normalize_for_diff(item, strict=strict) for item in obj]
    return obj


def _canonical_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"


def _canonical_lines(payload: dict[str, Any]) -> list[str]:
    return _canonical_text(payload).splitlines(keepends=True)


def _console_for_stdout(*, color: bool) -> Console:
    return Console(file=sys.stdout, force_terminal=color and sys.stdout.isatty())


def _print_unified_inline_diff(
    lines_a: list[str],
    lines_b: list[str],
    *,
    color: bool,
) -> None:
    """Word-style highlights within changed JSON lines (editor-like inline view)."""
    console = _console_for_stdout(color=color)
    table = Table(show_header=False, box=None, pad_edge=False, collapse_padding=True)
    table.add_column("source", ratio=1)
    table.add_column("destination", ratio=1)

    matcher = SequenceMatcher(a=lines_a, b=lines_b)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for la, lb in zip(lines_a[i1:i2], lines_b[j1:j2], strict=True):
                table.add_row(
                    Text(la.rstrip("\n"), style="dim"),
                    Text(lb.rstrip("\n"), style="dim"),
                )
            continue
        if tag == "replace":
            left = "".join(lines_a[i1:i2])
            right = "".join(lines_b[j1:j2])
            sm = SequenceMatcher(a=left, b=right)
            tl = Text()
            tr = Text()
            for t2, a0, a1, b0, b1 in sm.get_opcodes():
                if t2 == "equal":
                    tl.append(left[a0:a1])
                    tr.append(right[b0:b1])
                elif t2 == "delete":
                    tl.append(left[a0:a1], style="bold red" if color else "")
                elif t2 == "insert":
                    tr.append(right[b0:b1], style="bold green" if color else "")
                else:
                    tl.append(left[a0:a1], style="bold red" if color else "")
                    tr.append(right[b0:b1], style="bold green" if color else "")
            table.add_row(tl, tr)
            continue
        if tag == "delete":
            block = "".join(lines_a[i1:i2])
            table.add_row(
                Text(block.rstrip("\n"), style="bold red" if color else ""),
                Text("", style="dim"),
            )
        elif tag == "insert":
            block = "".join(lines_b[j1:j2])
            table.add_row(
                Text("", style="dim"),
                Text(block.rstrip("\n"), style="bold green" if color else ""),
            )

    console.print(table)


def _print_side_by_side_json(
    a_payload: dict[str, Any],
    b_payload: dict[str, Any],
    spec_a: str,
    spec_b: str,
) -> None:
    console = _console_for_stdout(color=sys.stdout.isatty())
    left = Syntax(
        _canonical_text(a_payload),
        "json",
        theme="ansi_dark",
        line_numbers=True,
        word_wrap=True,
    )
    right = Syntax(
        _canonical_text(b_payload),
        "json",
        theme="ansi_dark",
        line_numbers=True,
        word_wrap=True,
    )
    console.print(
        Columns(
            [
                Panel(left, title=f"source ({spec_a})", border_style="blue"),
                Panel(right, title=f"destination ({spec_b})", border_style="magenta"),
            ],
            equal=True,
            expand=True,
        )
    )


def cmd_diff(
    spec_a: str,
    spec_b: str,
    *,
    strict: bool,
    output_format: str,
    cwd: Path | None,
) -> None:
    """Load two spaces and compare canonical JSON with optional normalization."""
    fmt: DiffFormat = (
        "side-by-side" if output_format.lower() == "side-by-side" else "unified"
    )
    # Resolve endpoint + load credentials outside the broad ``except Exception``
    # below: load_config_or_exit raises typer.Exit (a RuntimeError) that the
    # broad handler would otherwise swallow into a misleading exit 1.
    try:
        slot_a, space_id_a = parse_source_endpoint(spec_a)
    except EndpointParseError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)
    cfg_a = load_config_or_exit(slot_a, cwd)
    try:
        a_raw = dict(
            Space.get_space(cfg_a.user_id, cfg_a.company_id, space_id_a),
        )
    except Exception as exc:
        typer.echo(f"diff failed fetching --source space ({spec_a!r}): {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg_a, exc, label=f"space diff --source ({spec_a!r})"
        )
        sys.exit(1)

    try:
        slot_b, space_id_b = parse_source_endpoint(spec_b)
    except EndpointParseError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)
    cfg_b = load_config_or_exit(slot_b, cwd)
    try:
        b_raw = dict(
            Space.get_space(cfg_b.user_id, cfg_b.company_id, space_id_b),
        )
    except Exception as exc:
        typer.echo(
            f"diff failed fetching --destination space ({spec_b!r}): {exc}", err=True
        )
        echo_credential_debug_if_auth_failure(
            cfg_b, exc, label=f"space diff --destination ({spec_b!r})"
        )
        sys.exit(1)

    a_payload = a_raw if strict else _normalize_for_diff(a_raw, strict=False)
    b_payload = b_raw if strict else _normalize_for_diff(b_raw, strict=False)

    text_a = json.dumps(a_payload, sort_keys=True, default=str)
    text_b = json.dumps(b_payload, sort_keys=True, default=str)
    if text_a == text_b:
        typer.echo("No differences.")
        return

    use_color = sys.stdout.isatty()

    if fmt == "side-by-side":
        _print_side_by_side_json(a_payload, b_payload, spec_a, spec_b)
        typer.echo("", err=True)
        if strict:
            typer.echo(
                "Tip: full payloads still differ. "
                "Use --format unified for a line/word-oriented diff.",
                err=True,
            )
        else:
            typer.echo(
                "Tip: payloads still differ after normalization. "
                "Use --format unified for a line/word-oriented diff, or --strict to include ids/timestamps.",
                err=True,
            )
        sys.exit(1)

    lines_a = _canonical_lines(a_payload)
    lines_b = _canonical_lines(b_payload)

    if use_color:
        console = _console_for_stdout(color=True)
        if strict:
            console.print("[dim]Diff (full payloads)[/dim]")
        else:
            console.print(
                "[dim]Diff (normalized JSON; use --strict for full payloads)[/dim]"
            )
        _print_unified_inline_diff(lines_a, lines_b, color=True)
        sys.exit(1)

    diff_lines = list(
        unified_diff(
            lines_a,
            lines_b,
            fromfile=f"source ({spec_a})",
            tofile=f"destination ({spec_b})",
            lineterm="\n",
        )
    )
    sys.stdout.writelines(diff_lines)
    sys.exit(1)
