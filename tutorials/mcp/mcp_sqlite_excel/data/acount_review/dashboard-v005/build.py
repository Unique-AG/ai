#!/usr/bin/env python3
"""Combine HTML page fragments into the single-file platform artifact.

Configuration (lowest → highest precedence)
-------------------------------------------
1. ``src/config.json``
2. Environment variables: ``DASHBOARD_MCP_SERVER``, ``DASHBOARD_RM_NAME``,
   ``DASHBOARD_PAGE_TITLE``, ``DASHBOARD_POLL_MS``, ``DASHBOARD_CONNECTORS_ONLINE``
3. CLI flags: ``--mcp-server``, ``--rm-name``, …

Examples::

    python build.py
    python build.py --mcp-server mcp_xxxxxxxx
    DASHBOARD_MCP_SERVER=mcp_xxxxxxxx python build.py

→ writes ``../dashboard-v005.html``

Business data is live via ``data-unique-*``; this build only inlines CSS and
substitutes ``__PLACEHOLDER__`` tokens from config.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PAGES = SRC / "pages"
CONFIG_PATH = SRC / "config.json"
BUILD_PAGES = ROOT / "build" / "pages"
DEFAULT_OUT = ROOT.parent / "dashboard-v005.html"

# config.json key → placeholder name (without __)
CONFIG_KEYS = {
    "mcp_server": "MCP_SERVER",
    "rm_name": "RM_NAME",
    "page_title": "PAGE_TITLE",
    "poll_ms": "POLL_MS",
    "connectors_online": "CONNECTORS_ONLINE",
}

ENV_KEYS = {
    "mcp_server": "DASHBOARD_MCP_SERVER",
    "rm_name": "DASHBOARD_RM_NAME",
    "page_title": "DASHBOARD_PAGE_TITLE",
    "poll_ms": "DASHBOARD_POLL_MS",
    "connectors_online": "DASHBOARD_CONNECTORS_ONLINE",
}

DEFAULTS = {
    "mcp_server": "",
    "rm_name": "Elena",
    "page_title": "Account Review — MCP Data Console",
    "poll_ms": 15000,
    "connectors_online": 3,
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def fill(template: str, mapping: dict) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace(f"__{key}__", str(value))
    return out


def require_filled(text: str, *, context: str) -> str:
    leftover = sorted(set(re.findall(r"__[A-Z0-9_]+__", text)))
    if leftover:
        raise SystemExit(f"{context}: unresolved placeholders: {', '.join(leftover)}")
    return text


def load_config(cli: argparse.Namespace) -> dict:
    """Merge defaults ← config.json ← env ← CLI."""
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.is_file():
        file_cfg = json.loads(read(CONFIG_PATH))
        for key in CONFIG_KEYS:
            if key in file_cfg and file_cfg[key] not in (None, ""):
                cfg[key] = file_cfg[key]

    for key, env_name in ENV_KEYS.items():
        raw = os.environ.get(env_name)
        if raw is not None and raw != "":
            cfg[key] = int(raw) if key in ("poll_ms", "connectors_online") else raw

    if cli.mcp_server:
        cfg["mcp_server"] = cli.mcp_server
    if cli.rm_name:
        cfg["rm_name"] = cli.rm_name
    if cli.page_title:
        cfg["page_title"] = cli.page_title
    if cli.poll_ms is not None:
        cfg["poll_ms"] = cli.poll_ms
    if cli.connectors_online is not None:
        cfg["connectors_online"] = cli.connectors_online

    if not cfg["mcp_server"]:
        raise SystemExit("mcp_server is required. Set it in src/config.json, DASHBOARD_MCP_SERVER, or --mcp-server.")
    cfg["poll_ms"] = int(cfg["poll_ms"])
    cfg["connectors_online"] = int(cfg["connectors_online"])
    return cfg


def placeholder_mapping(cfg: dict) -> dict:
    return {token: cfg[key] for key, token in CONFIG_KEYS.items()}


def build(out_path: Path, cfg: dict) -> Path:
    mapping = placeholder_mapping(cfg)
    manifest = json.loads(read(PAGES / "manifest.json"))

    if BUILD_PAGES.exists():
        shutil.rmtree(BUILD_PAGES)
    BUILD_PAGES.mkdir(parents=True)

    chunks = []
    for entry in manifest["order"]:
        page_path = PAGES / entry
        if not page_path.is_file():
            raise SystemExit(f"manifest references missing page: {page_path}")
        body = require_filled(
            fill(read(page_path).rstrip("\n"), mapping),
            context=entry,
        )
        write(BUILD_PAGES / entry, body)
        label = entry.replace(".html", "").replace("_", " ").upper()
        chunks.append(f"    <!-- ===== {label} ===== -->")
        chunks.append(body)

    css = read(SRC / "styles.css")
    css_indented = "\n".join(("      " + line) if line.strip() else "" for line in css.splitlines())

    document = require_filled(
        fill(
            read(SRC / "shell.html"),
            {
                **mapping,
                "STYLES": css_indented,
                "PAGES": "\n\n".join(chunks),
            },
        ),
        context="shell.html",
    )
    write(out_path, document)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output HTML path (default: {DEFAULT_OUT.name})",
    )
    parser.add_argument(
        "--mcp-server",
        help="Unique MCP connector id (overrides config.json / env)",
    )
    parser.add_argument("--rm-name", help="Greeting name (default from config)")
    parser.add_argument("--page-title", help="HTML <title>")
    parser.add_argument(
        "--poll-ms",
        type=int,
        help="data-unique-source-poll interval in ms",
    )
    parser.add_argument(
        "--connectors-online",
        type=int,
        help="Footer connector count label",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print resolved config and exit",
    )
    args = parser.parse_args()
    cfg = load_config(args)
    if args.print_config:
        print(json.dumps(cfg, indent=2))
        return

    path = build(args.output.resolve(), cfg)
    print(f"mcp_server={cfg['mcp_server']}")
    print(f"Combined {len(list(BUILD_PAGES.glob('*.html')))} pages → {path}")
    print(f"({path.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
