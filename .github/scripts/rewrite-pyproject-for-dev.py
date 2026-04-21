#!/usr/bin/env python3
"""Rewrite a package's pyproject.toml for a .devN build.

For a dev publish at target version `YYYY.WW.0.devN`:
  1. Replace the package's own `project.version` with the dev version.
  2. In every PEP 621 dependency array (`project.dependencies` and each
     entry of `project.optional-dependencies`), for any requirement that
     references another AI monorepo package, rewrite the specifier to
     `>=<dev_version>`, e.g.
         "unique-sdk>=0.10.85,<0.12"  ->  "unique-sdk>=2026.18.0.dev7"
         "unique-toolkit[monitoring]>=1.69.6,<2"
             ->  "unique-toolkit[monitoring]>=2026.18.0.dev7"

Because the constraint explicitly contains a PEP 440 pre-release segment
(`devN`), pip/uv will resolve to dev versions without `--pre`.

Non-AI dependencies are left untouched. `project.name` and `[tool.*]` tables
are never touched.

Usage:
    rewrite-pyproject-for-dev.py <pyproject.toml> <dev-version>

The file is rewritten in place using tomlkit so formatting/comments are
preserved.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import tomlkit

AI_PACKAGES = {
    "unique-sdk",
    "unique-toolkit",
    "unique-mcp",
    "unique-orchestrator",
    "unique-web-search",
    "unique-swot",
    "unique-deep-research",
    "unique-internal-search",
    "unique-follow-up-questions",
    "unique-stock-ticker",
    "unique-quartr",
    "unique-six",
}

_REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)(\[[^\]]*\])?\s*(.*)$")


def rewrite_req(raw: str, dev_version: str) -> str:
    m = _REQ_RE.match(raw)
    if not m:
        return raw
    name, extras = m.group(1), m.group(2) or ""
    if name.lower() not in AI_PACKAGES:
        return raw
    return f"{name}{extras}>={dev_version}"


def rewrite_array(arr, dev_version: str) -> None:
    for i, item in enumerate(arr):
        if isinstance(item, str):
            arr[i] = rewrite_req(item, dev_version)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    pyproject = Path(sys.argv[1])
    dev_version = sys.argv[2]
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d+(\.dev\d+)?", dev_version):
        raise SystemExit(f"invalid dev version: {dev_version!r}")

    doc = tomlkit.parse(pyproject.read_text())
    project = doc.get("project")
    if project is None:
        raise SystemExit(f"{pyproject}: no [project] table")

    project["version"] = dev_version

    deps = project.get("dependencies")
    if deps is not None:
        rewrite_array(deps, dev_version)

    opt_deps = project.get("optional-dependencies")
    if opt_deps is not None:
        for _group, items in opt_deps.items():
            rewrite_array(items, dev_version)

    pyproject.write_text(tomlkit.dumps(doc))
    print(f"{pyproject}: version -> {dev_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
