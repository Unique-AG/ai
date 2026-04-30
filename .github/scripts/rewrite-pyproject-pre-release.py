#!/usr/bin/env python3
"""Rewrite a package's pyproject.toml for a pre-release build.

Used by both the dev (``.devN``) and release-candidate (``rcN``)
publish workflows. Two things happen in place:

1. ``project.version`` is replaced with the caller's ``--own-version``.
2. In every PEP 621 dependency array (``project.dependencies`` and each
   entry of ``project.optional-dependencies``), any requirement that
   names another AI monorepo package is rewritten to use the pin
   supplied via ``--dep-pins``. For example, with::

       --dep-pins '{"unique-sdk": ">=2026.18.0.dev3,<2026.18.0rc0",
                    "unique-toolkit": ">=2026.18.0.dev7,<2026.18.0rc0"}'

   the rewriter produces::

       "unique-sdk>=0.10.85,<0.12"  ->  "unique-sdk>=2026.18.0.dev3,<2026.18.0rc0"
       "unique-toolkit[monitoring]>=1.69.6,<2"
           ->  "unique-toolkit[monitoring]>=2026.18.0.dev7,<2026.18.0rc0"

Because the constraint explicitly contains a PEP 440 pre-release segment
(``devN`` or ``rcN``), pip/uv resolves to pre-release versions without
``--pre``.

The pin map is computed upstream by either ``resolve-dev-versions.py``
or ``resolve-rc-versions.py``:

  * Dev publish (``resolve-dev-versions.py``) emits ``>=V,<YYY.WW.Prc0``
    pins for CalVer ``*.devN`` siblings; legacy fallbacks stay ``>=`` only.
  * RC publish (``resolve-rc-versions.py``) emits ``>=<version>`` pins,
    floored at the shared ``{cycle}.0rcN`` so customers can upgrade
    freely to later rcs or the final stable.

Non-AI dependencies are left untouched. ``project.name`` and ``[tool.*]``
tables are never touched. Formatting and comments in the TOML file are
preserved via tomlkit.

Usage:
    rewrite-pyproject-pre-release.py <pyproject.toml>
        --own-version <v> --dep-pins <json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import tomlkit

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from calver_dev_dependency_pin import is_valid_rewrite_dep_pin  # noqa: E402

_REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)(\[[^\]]*\])?\s*(.*)$")
# Own version is always a CalVer pre-release — either ``.devN`` (dev
# publish) or ``rcN`` (release-candidate publish). Stable CalVers are
# stamped by release-please, never by this script.
_VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d+(\.dev\d+|rc\d+)$")
# Dep pins from resolvers: ``>=`` with optional ``,<YYY.WW.Prc0`` for dev
# siblings, ``==`` for rc cuts, or legacy ``>=`` only.


def normalize(name: str) -> str:
    # PEP 503 normalization — unify "-", "_", ".".
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
    return new, (raw, new)


def rewrite_array(
    arr, dep_pins: dict[str, str], changes: list[tuple[str, str]]
) -> None:
    for i, item in enumerate(arr):
        if isinstance(item, str):
            new, change = rewrite_req(item, dep_pins)
            if change is not None:
                changes.append(change)
                arr[i] = new


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pyproject", type=Path)
    parser.add_argument("--own-version", required=True)
    parser.add_argument(
        "--dep-pins",
        required=True,
        help="JSON object mapping PEP 503 normalized name -> spec suffix",
    )
    args = parser.parse_args(argv)

    if not _VERSION_RE.match(args.own_version):
        raise SystemExit(f"invalid --own-version: {args.own_version!r}")

    dep_pins_raw = json.loads(args.dep_pins)
    if not isinstance(dep_pins_raw, dict):
        raise SystemExit("--dep-pins must be a JSON object")

    dep_pins: dict[str, str] = {}
    for name, pin in dep_pins_raw.items():
        if not isinstance(pin, str) or not is_valid_rewrite_dep_pin(pin):
            raise SystemExit(f"invalid pin for {name!r}: {pin!r}")
        dep_pins[normalize(name)] = pin

    doc = tomlkit.parse(args.pyproject.read_text())
    project = doc.get("project")
    if project is None:
        raise SystemExit(f"{args.pyproject}: no [project] table")

    prev_version = str(project.get("version", "<unset>"))
    project["version"] = args.own_version

    changes: list[tuple[str, str]] = []

    deps = project.get("dependencies")
    if deps is not None:
        rewrite_array(deps, dep_pins, changes)

    opt_deps = project.get("optional-dependencies")
    if opt_deps is not None:
        for _group, items in opt_deps.items():
            rewrite_array(items, dep_pins, changes)

    args.pyproject.write_text(tomlkit.dumps(doc))

    print(f"{args.pyproject}:")
    print(f"  version: {prev_version} -> {args.own_version}")
    if changes:
        print(f"  dependencies rewritten ({len(changes)}):")
        for before, after in changes:
            print(f"    {before!r} -> {after!r}")
    else:
        print("  dependencies: no AI cross-deps to rewrite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
