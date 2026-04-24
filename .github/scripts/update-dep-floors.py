#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit"]
# ///
"""Rewrite cross-package dependency floors in all pyproject.toml files.

Reads ``.release-please-manifest.json`` to discover the current stable version
of every AI package, then walks every ``pyproject.toml`` in the repo and
rewrites ``>=OLD`` floor constraints for those packages to ``>=CURRENT``.

The `project.version` field is **not** touched — only dependency floors.

Typical usage after a release:

    python .github/scripts/update-dep-floors.py

Or targeting a specific manifest / repo root:

    python .github/scripts/update-dep-floors.py \\
        --manifest .release-please-manifest.json \\
        --root .
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import tomlkit

_REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)(\[[^\]]*\])?\s*(.*)$")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def rewrite_req(
    raw: str, dep_pins: dict[str, str]
) -> tuple[str, tuple[str, str] | None]:
    m = _REQ_RE.match(raw)
    if not m:
        return raw, None
    name, extras = m.group(1), m.group(2) or ""
    pin = dep_pins.get(normalize(name))
    if pin is None:
        return raw, None
    new = f"{name}{extras}{pin}"
    if new == raw:
        return raw, None
    return new, (raw, new)


def rewrite_array(
    arr: list, dep_pins: dict[str, str], changes: list[tuple[str, str]]
) -> None:
    for i, item in enumerate(arr):
        if isinstance(item, str):
            new, change = rewrite_req(item, dep_pins)
            if change is not None:
                changes.append(change)
                arr[i] = new


def build_dep_pins(manifest: dict[str, str], config: dict) -> dict[str, str]:
    """Map normalized pypi-name -> '>=VERSION' from the manifest.

    The manifest keys are directory paths (e.g. 'unique_sdk',
    'tool_packages/unique_web_search').  The release-please config maps those
    same directory keys to component names (the PyPI name).  We join on the
    directory key to build the pypi-name -> version mapping.
    """
    packages = config.get("packages", {})
    pins: dict[str, str] = {}
    for dir_key, version in manifest.items():
        pkg_cfg = packages.get(dir_key, {})
        component = pkg_cfg.get("component")
        if component:
            pins[normalize(component)] = f">={version}"
    return pins


def update_file(pyproject: Path, dep_pins: dict[str, str]) -> list[tuple[str, str]]:
    doc = tomlkit.parse(pyproject.read_text())
    project = doc.get("project")
    if project is None:
        return []

    changes: list[tuple[str, str]] = []

    deps = project.get("dependencies")
    if deps is not None:
        rewrite_array(deps, dep_pins, changes)

    opt_deps = project.get("optional-dependencies")
    if opt_deps is not None:
        for _group, items in opt_deps.items():
            rewrite_array(items, dep_pins, changes)

    if changes:
        pyproject.write_text(tomlkit.dumps(doc))

    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(".release-please-manifest.json"),
        help="Path to .release-please-manifest.json (default: .release-please-manifest.json)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("release-please-config.json"),
        help="Path to release-please-config.json (default: release-please-config.json)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repo root to search for pyproject.toml files (default: .)",
    )
    args = parser.parse_args(argv)

    manifest: dict[str, str] = json.loads(args.manifest.read_text())
    config: dict = json.loads(args.config.read_text())
    dep_pins = build_dep_pins(manifest, config)

    if not dep_pins:
        raise SystemExit("No packages found in manifest/config — check paths.")

    print("Dependency floors from manifest:")
    for name, pin in sorted(dep_pins.items()):
        print(f"  {name}{pin}")
    print()

    total_changes = 0
    for pyproject in sorted(args.root.rglob("pyproject.toml")):
        if any(
            part in {".venv", ".git", "__pycache__", "dist", "node_modules"}
            for part in pyproject.parts
        ):
            continue
        if not pyproject.is_file():
            continue
        changes = update_file(pyproject, dep_pins)
        if changes:
            total_changes += len(changes)
            print(f"{pyproject}:")
            for before, after in changes:
                print(f"  {before!r} -> {after!r}")

    if total_changes == 0:
        print("All dependency floors are already up to date.")
    else:
        print(f"\nTotal: {total_changes} floor(s) updated.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
