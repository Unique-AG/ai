#!/usr/bin/env python3
"""Combine HTML page fragments into the single-file platform artifact.

Configuration (lowest → highest precedence)
-------------------------------------------
1. ``src/config.json``
2. Environment variables: ``DASHBOARD_MCP_SERVER``, ``DASHBOARD_RM_NAME``,
   ``DASHBOARD_PAGE_TITLE``, ``DASHBOARD_POLL_MS``, ``DASHBOARD_CONNECTORS_ONLINE``,
   ``DASHBOARD_OUTPUT``
3. CLI flags: ``--mcp-server``, ``--rm-name``, …, ``--output``/``-o``

Examples::

    python build.py
    python build.py --mcp-server mcp_xxxxxxxx
    DASHBOARD_MCP_SERVER=mcp_xxxxxxxx python build.py

    # Spin up a second, differently-named dashboard from the same src/:
    python build.py --output ../dashboard-onboarding-demo.html
    DASHBOARD_OUTPUT=../dashboard-onboarding-demo.html python build.py

→ writes ``output`` (``src/config.json``'s ``output`` key, default
``../dashboard-v005.html``, relative to this folder).

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
TEMPLATES = SRC / "templates"
CONFIG_PATH = SRC / "config.json"
CASES_PATH = SRC / "cases.json"
BUILD_PAGES = ROOT / "build" / "pages"
DEFAULT_OUT = ROOT.parent / "dashboard-v005.html"

CASE_ACTIONBARS_MARKER = "<!-- __CASE_ACTIONBARS__ -->"
CASE_FIGURES_MARKER = "<!-- __CASE_FIGURES__ -->"
CASE_VISIBILITY_MARKER = "/* __CASE_VISIBILITY_CSS__ */"
CASE_BADGE_MARKER = "/* __CASE_BADGE_CSS__ */"
CASE_BARS_MARKER = "/* __CASE_BARS_CSS__ */"
CASE_OPEN_SECTIONS_MARKER = "/* __CASE_OPEN_SECTIONS_CSS__ */"

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

# Output path is config-driven too, but it's a destination, not a
# __PLACEHOLDER__ substituted into the document — kept out of CONFIG_KEYS.
OUTPUT_KEY = "output"
OUTPUT_ENV = "DASHBOARD_OUTPUT"


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
    cfg[OUTPUT_KEY] = ""
    if CONFIG_PATH.is_file():
        file_cfg = json.loads(read(CONFIG_PATH))
        for key in CONFIG_KEYS:
            if key in file_cfg and file_cfg[key] not in (None, ""):
                cfg[key] = file_cfg[key]
        if file_cfg.get(OUTPUT_KEY):
            cfg[OUTPUT_KEY] = file_cfg[OUTPUT_KEY]

    for key, env_name in ENV_KEYS.items():
        raw = os.environ.get(env_name)
        if raw is not None and raw != "":
            cfg[key] = int(raw) if key in ("poll_ms", "connectors_online") else raw
    output_env = os.environ.get(OUTPUT_ENV)
    if output_env:
        cfg[OUTPUT_KEY] = output_env

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
    if cli.output:
        cfg[OUTPUT_KEY] = str(cli.output)

    if not cfg["mcp_server"]:
        raise SystemExit("mcp_server is required. Set it in src/config.json, DASHBOARD_MCP_SERVER, or --mcp-server.")
    cfg["poll_ms"] = int(cfg["poll_ms"])
    cfg["connectors_online"] = int(cfg["connectors_online"])
    return cfg


def resolve_output_path(cfg: dict) -> Path:
    """Resolve the configured output path, relative to this dashboard folder."""
    raw = cfg.get(OUTPUT_KEY) or ""
    if not raw:
        return DEFAULT_OUT
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (ROOT / path).resolve()


def placeholder_mapping(cfg: dict) -> dict:
    return {token: cfg[key] for key, token in CONFIG_KEYS.items()}


def load_cases() -> list[dict]:
    """Load the RM use-case registry (src/cases.json)."""
    return json.loads(read(CASES_PATH))["cases"]


def rule_case_pairs(cases: list[dict]) -> list[tuple[str, dict]]:
    """Flatten each case's rule_codes into (rule_code, case) pairs.

    Two DB rule codes can share one case (e.g. R-SCR-ADVMEDIA / R-SCR-PEP both
    map to the "adverse-media" use case) — each still gets its own variant so
    the [data-rule=...] CSS match stays a simple equality check.
    """
    pairs: list[tuple[str, dict]] = []
    for case in cases:
        for rule_code in case["rule_codes"]:
            pairs.append((rule_code, case))
    return pairs


def render_case_actionbars(cases: list[dict], mapping: dict) -> str:
    """Expand the action-bar partial(s) into one block per rule_code.

    Most cases render ``templates/actionbar_case.html`` (single smart-action
    button, live-labeled from ``action_button``). A case with a
    ``dual_action`` entry (e.g. regulatory change: "Email client" vs
    "Escalate to compliance") renders ``actionbar_case_dual.html`` instead —
    same reusable shell, two fixed-label buttons.
    """
    single_partial = read(TEMPLATES / "actionbar_case.html").rstrip("\n")
    dual_partial = read(TEMPLATES / "actionbar_case_dual.html").rstrip("\n")
    blocks = []
    for rule_code, case in rule_case_pairs(cases):
        base_mapping = {
            **mapping,
            "RULE_CODE": rule_code,
            "CASE_ICON": case["icon"],
            "CASE_TAG": case["tag"],
        }
        dual = case.get("dual_action")
        if dual:
            action1, action2 = dual["actions"]
            case_mapping = {
                **base_mapping,
                "ACTION1_LABEL": action1["label"],
                "ACTION1_TOAST": action1["toast"],
                "ACTION1_INSTRUCTIONS": action1["instructions"],
                "ACTION2_LABEL": action2["label"],
                "ACTION2_TOAST": action2["toast"],
                "ACTION2_INSTRUCTIONS": action2["instructions"],
            }
            partial = dual_partial
        else:
            case_mapping = {**base_mapping, "CASE_INSTRUCTIONS": case["instructions"]}
            partial = single_partial
        blocks.append(
            require_filled(
                fill(partial, case_mapping),
                context=f"actionbar template ({rule_code})",
            )
        )
    return "\n".join(blocks)


def render_case_figures(cases: list[dict]) -> str:
    """Expand src/templates/figure_case.html into one block per rule_code.

    Most cases render a single figure (``fig1..3_*`` fields, class
    ``case-figure``). A case with a ``figure2_title`` renders a second,
    independent block from the same reusable template — just a different
    field prefix (``perf1..3_*``) and CSS class (``case-figure2``) so the
    two can coexist on one row without colliding.

    A case without a ``figure_title`` (suit-alloc, suit-review, reg-change)
    is skipped entirely here — its figure content was promoted to an
    always-visible generic section in clients.html instead (Portfolio and
    Mandate, Suitability Profile, Holdings and Categorization), so it no
    longer needs its own case-gated figure.
    """
    partial = read(TEMPLATES / "figure_case.html").rstrip("\n")
    blocks = []
    for rule_code, case in rule_case_pairs(cases):
        if "figure_title" not in case:
            continue
        case_mapping = {
            "RULE_CODE": rule_code,
            "FIGURE_TITLE": case["figure_title"],
            "FIGURE_CLASS": "case-figure",
            "FIG_PREFIX": "fig",
        }
        blocks.append(
            require_filled(
                fill(partial, case_mapping),
                context=f"templates/figure_case.html ({rule_code})",
            )
        )
        if case.get("figure2_title"):
            figure2_mapping = {
                "RULE_CODE": rule_code,
                "FIGURE_TITLE": case["figure2_title"],
                "FIGURE_CLASS": "case-figure2",
                "FIG_PREFIX": "perf",
            }
            blocks.append(
                require_filled(
                    fill(partial, figure2_mapping),
                    context=f"templates/figure_case.html (figure2, {rule_code})",
                )
            )
    return "\n".join(blocks)


def render_case_css(cases: list[dict]) -> tuple[str, str, str]:
    """Generate the [data-rule=...] visibility + badge-label + bar CSS from cases.json."""
    visibility_rules = []
    badge_rules = []
    bar_rules = []
    for rule_code, case in rule_case_pairs(cases):
        visibility_rules.append(
            f'.actionbar[data-rule="{rule_code}"] .actionbar-case[data-rule="{rule_code}"] {{\n'
            f"  display: flex;\n"
            f"}}\n"
            f'.detail[data-rule="{rule_code}"] .case-figure[data-rule="{rule_code}"] {{\n'
            f"  display: block;\n"
            f"}}"
        )
        if case.get("figure2_title"):
            visibility_rules.append(
                f'.detail[data-rule="{rule_code}"] .case-figure2[data-rule="{rule_code}"] {{\n  display: block;\n}}'
            )
        label = f"{case['icon']} {case['tag']}".replace('"', '\\"')
        badge_rules.append(f'.case-badge[data-rule="{rule_code}"]::before {{\n  content: "{label}";\n}}')
        if case.get("figure_bars"):
            bar_rules.append(f'.case-figure[data-rule="{rule_code}"] .figbar {{\n  display: block;\n}}')
    return "\n".join(visibility_rules), "\n".join(badge_rules), "\n".join(bar_rules)


def render_open_sections_css(cases: list[dict]) -> str:
    """Generate CSS that force-opens generic sections relevant to a case.

    ``open_sections`` on a case (e.g. ``["history"]``) names ``.sec[data-key=…]``
    elements on the client detail page (see clients.html) that should render
    expanded — regardless of their default collapsed state — whenever that
    row's live ``rule_code`` matches. Unrelated sections keep their normal
    collapsible behaviour; this only overrides the ones called out per case.
    """
    rules = []
    for rule_code, case in rule_case_pairs(cases):
        for key in case.get("open_sections", []):
            rules.append(
                f'.detail[data-rule="{rule_code}"] .sec[data-key="{key}"] > .sec-body {{\n'
                f"  display: block;\n"
                f"}}\n"
                f'.detail[data-rule="{rule_code}"] .sec[data-key="{key}"] > .sec-sum .sec-chev {{\n'
                f"  transform: rotate(90deg);\n"
                f"}}"
            )
    return "\n".join(rules)


def build(out_path: Path, cfg: dict) -> Path:
    mapping = placeholder_mapping(cfg)
    manifest = json.loads(read(PAGES / "manifest.json"))
    cases = load_cases()
    case_actionbars = render_case_actionbars(cases, mapping)
    case_figures = render_case_figures(cases)
    case_visibility_css, case_badge_css, case_bars_css = render_case_css(cases)
    case_open_sections_css = render_open_sections_css(cases)

    if BUILD_PAGES.exists():
        shutil.rmtree(BUILD_PAGES)
    BUILD_PAGES.mkdir(parents=True)

    chunks = []
    for entry in manifest["order"]:
        page_path = PAGES / entry
        if not page_path.is_file():
            raise SystemExit(f"manifest references missing page: {page_path}")
        body = fill(read(page_path).rstrip("\n"), mapping)
        body = body.replace(CASE_ACTIONBARS_MARKER, case_actionbars)
        body = body.replace(CASE_FIGURES_MARKER, case_figures)
        body = require_filled(body, context=entry)
        write(BUILD_PAGES / entry, body)
        label = entry.replace(".html", "").replace("_", " ").upper()
        chunks.append(f"    <!-- ===== {label} ===== -->")
        chunks.append(body)

    css = read(SRC / "styles.css")
    css = css.replace(CASE_VISIBILITY_MARKER, case_visibility_css)
    css = css.replace(CASE_BADGE_MARKER, case_badge_css)
    css = css.replace(CASE_BARS_MARKER, case_bars_css)
    css = css.replace(CASE_OPEN_SECTIONS_MARKER, case_open_sections_css)
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
        default=None,
        help=(
            "Output HTML path, relative to this folder unless absolute "
            f"(overrides config.json / DASHBOARD_OUTPUT; default: {DEFAULT_OUT.name})"
        ),
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
    out_path = resolve_output_path(cfg)
    if args.print_config:
        print(json.dumps({**cfg, "resolved_output": str(out_path)}, indent=2))
        return

    path = build(out_path, cfg)
    print(f"mcp_server={cfg['mcp_server']}")
    print(f"Combined {len(list(BUILD_PAGES.glob('*.html')))} pages → {path}")
    print(f"({path.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
