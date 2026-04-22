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


def _normalize(name: str) -> str:
    # PEP 503 project name normalization — underscores and dots collapse
    # to hyphens, so `unique_toolkit`, `unique.toolkit` and `unique-toolkit`
    # all compare equal.
    return re.sub(r"[-_.]+", "-", name).lower()


_AI_PACKAGES_NORMALIZED = {_normalize(n) for n in AI_PACKAGES}


def rewrite_req(raw: str, dev_version: str) -> tuple[str, bool]:
    m = _REQ_RE.match(raw)
    if not m:
        return raw, False
    name, extras = m.group(1), m.group(2) or ""
    if _normalize(name) not in _AI_PACKAGES_NORMALIZED:
        return raw, False
    return f"{name}{extras}>={dev_version}", True


def rewrite_array(arr, dev_version: str, changes: list[tuple[str, str]]) -> None:
    for i, item in enumerate(arr):
        if isinstance(item, str):
            new, changed = rewrite_req(item, dev_version)
            if changed:
                changes.append((item, new))
                arr[i] = new


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

    prev_version = str(project.get("version", "<unset>"))
    project["version"] = dev_version

    changes: list[tuple[str, str]] = []

    deps = project.get("dependencies")
    if deps is not None:
        rewrite_array(deps, dev_version, changes)

    opt_deps = project.get("optional-dependencies")
    if opt_deps is not None:
        for _group, items in opt_deps.items():
            rewrite_array(items, dev_version, changes)

    pyproject.write_text(tomlkit.dumps(doc))

    print(f"{pyproject}:")
    print(f"  version: {prev_version} -> {dev_version}")
    if changes:
        print(f"  dependencies rewritten ({len(changes)}):")
        for before, after in changes:
            print(f"    {before!r} -> {after!r}")
    else:
        print("  dependencies: no AI cross-deps to rewrite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
