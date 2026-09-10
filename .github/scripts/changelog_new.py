#!/usr/bin/env python3
"""Create a client-facing changelog fragment under ``.changelog/unreleased/``.

This is a dependency-light stand-in for ``changie new`` (https://changie.dev):
the AI repo has no Node/Go toolchain, so instead of shelling out to the
``changie`` binary we write the same YAML the monorepo's ``uq changelog new``
produces. The fragment is later copied verbatim into Unique-AG/monorepo by its
"Release · Sync AI Versions" workflow and batched into the platform release
notes there, which is why the schema (``.changie.yaml``) must stay identical
between the two repositories.

Usage (non-interactive, the only mode)::

    uv run poe changelog-new \\
        --kind Fixed \\
        --component "API / SDK" \\
        --body "Short, client-facing description of the fix." \\
        --custom Audience=user \\
        --custom Ticket=UN-12345

Allowed values for ``--kind``, ``--component`` and ``Audience`` are read from
``.changie.yaml``; ``Ticket`` is optional and must be one or more ``UN-<n>``
keys separated by commas.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / ".changie.yaml"

TICKET_RE = re.compile(r"^UN-[0-9]+$")


class FragmentError(ValueError):
    """Raised when the requested fragment does not satisfy ``.changie.yaml``."""


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise FragmentError(f"{path}: expected a mapping at the top level.")
    return config


def allowed_kinds(config: dict[str, Any]) -> list[str]:
    return [str(kind["label"]) for kind in config.get("kinds", [])]


def allowed_components(config: dict[str, Any]) -> list[str]:
    return [str(component) for component in config.get("components", [])]


def allowed_audiences(config: dict[str, Any]) -> list[str]:
    for custom in config.get("custom", []):
        if custom.get("key") == "Audience":
            return [str(option) for option in custom.get("enumOptions", [])]
    return []


def parse_custom(pairs: list[str]) -> dict[str, str]:
    """Turn repeated ``Key=Value`` flags into a mapping.

    Mirrors ``changie new --custom``; the value may itself contain ``=``
    (only the first one splits) and commas (no CSV splitting is applied).
    """
    custom: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        key = key.strip()
        value = value.strip()
        if not sep or not key:
            raise FragmentError(f"--custom expects Key=Value, got {pair!r}.")
        if key in custom:
            raise FragmentError(f"--custom {key} given more than once.")
        custom[key] = value
    return custom


def validate_ticket(ticket: str) -> str:
    """Normalise a comma-separated ticket list, failing on malformed keys."""
    entries = [entry.strip() for entry in ticket.split(",")]
    bad = [entry for entry in entries if not TICKET_RE.match(entry)]
    if bad:
        raise FragmentError(
            f"custom.Ticket entries must match UN-<number>; invalid: {', '.join(repr(entry) for entry in bad)}."
        )
    return ", ".join(entries)


def build_fragment(
    *,
    config: dict[str, Any],
    kind: str,
    component: str,
    body: str,
    custom: dict[str, str],
    now: dt.datetime,
) -> dict[str, Any]:
    kinds = allowed_kinds(config)
    components = allowed_components(config)
    audiences = allowed_audiences(config)

    if kind not in kinds:
        raise FragmentError(f"--kind {kind!r} is not one of: {', '.join(kinds)}.")
    if component not in components:
        raise FragmentError(
            f"--component {component!r} is not one of: {', '.join(components)}."
        )
    body = body.strip()
    if not body:
        raise FragmentError("--body must not be empty.")
    if re.search(r"\bUN-[0-9]+\b", body):
        raise FragmentError(
            "--body must not contain Jira ticket keys; pass them via --custom Ticket=UN-12345 instead."
        )

    unknown = sorted(set(custom) - {"Audience", "Ticket"})
    if unknown:
        raise FragmentError(f"Unknown --custom key(s): {', '.join(unknown)}.")

    audience = custom.get("Audience", "")
    if audience not in audiences:
        raise FragmentError(
            f"--custom Audience is required and must be one of: {', '.join(audiences)} (got {audience!r})."
        )

    fragment_custom: dict[str, str] = {"Audience": audience}
    ticket = custom.get("Ticket", "").strip()
    if ticket:
        fragment_custom["Ticket"] = validate_ticket(ticket)

    return {
        "component": component,
        "kind": kind,
        "body": body,
        "time": now.isoformat(),
        "custom": fragment_custom,
    }


def fragment_filename(kind: str, component: str, now: dt.datetime) -> str:
    """Reproduce changie's ``fragmentFileFormat`` from ``.changie.yaml``.

    ``{{.Kind | lower}}-{{.Component | replace " " "-" | replace "/" "-" | lower}}-{{.Time.Format "20060102-150405"}}``
    """
    slug = component.replace(" ", "-").replace("/", "-").lower()
    return f"{kind.lower()}-{slug}-{now.strftime('%Y%m%d-%H%M%S')}.yaml"


def render_fragment(fragment: dict[str, Any]) -> str:
    return yaml.safe_dump(
        fragment,
        sort_keys=False,
        indent=4,
        allow_unicode=True,
        width=float("inf"),
    )


def write_fragment(
    fragment: dict[str, Any], *, config: dict[str, Any], now: dt.datetime
) -> Path:
    changes_dir = REPO_ROOT / str(config.get("changesDir", ".changelog"))
    unreleased_dir = changes_dir / str(config.get("unreleasedDir", "unreleased"))
    unreleased_dir.mkdir(parents=True, exist_ok=True)
    target = unreleased_dir / fragment_filename(
        fragment["kind"], fragment["component"], now
    )
    if target.exists():
        raise FragmentError(f"{target} already exists; retry in a second.")
    target.write_text(render_fragment(fragment), encoding="utf-8")
    return target


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="changelog-new",
        description="Write a Changie-compatible changelog fragment to .changelog/unreleased/.",
    )
    parser.add_argument(
        "--kind", required=True, help="Added | Changed | Fixed | Removed | Security"
    )
    parser.add_argument(
        "--component", required=True, help='e.g. "API / SDK", "Conduct", "Web Search"'
    )
    parser.add_argument(
        "--body",
        required=True,
        help="Client-facing description. No ticket keys here; use --custom Ticket=UN-12345.",
    )
    parser.add_argument(
        "--custom",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable. Audience=user|admin|operator is required; Ticket=UN-12345[, UN-6789] is optional.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the fragment instead of writing it.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    now = dt.datetime.now().astimezone()
    try:
        config = load_config(args.config)
        fragment = build_fragment(
            config=config,
            kind=args.kind,
            component=args.component,
            body=args.body,
            custom=parse_custom(args.custom),
            now=now,
        )
        if args.dry_run:
            sys.stdout.write(render_fragment(fragment))
            return 0
        target = write_fragment(fragment, config=config, now=now)
    except FragmentError as exc:
        print(f"changelog-new: {exc}", file=sys.stderr)
        return 1
    print(f"changelog-new: wrote {target.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
