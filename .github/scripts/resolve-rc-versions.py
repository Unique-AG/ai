#!/usr/bin/env python3
"""Resolve rc versions and exact dep pins for an rc publish run.

Unlike dev publishes (per-package contiguous ``devN`` counters), an rc
cut republishes **every** publishable AI package at a single shared
``{cycle}.0rcN`` version. The shared counter is what lets sibling deps
be pinned with ``>=``: every package in the cut lands at the same
``rcN`` floor, so ``pip install`` pulls a mutually consistent set while
still allowing natural upgrades to later rcs or the final stable.

Counter selection
=================
For the chosen cycle, query PyPI for the highest ``rcN`` already
published against any publishable package, and emit ``rc(N+1)`` (or
``rc1`` if nothing exists yet). PyPI is the source of truth, so two rc
workflows running in parallel can never land on the same N — whichever
publishes first wins, and the second observes it and steps to the next
counter. Within the workflow the publish step itself is also serialized
under the ``publish-prerelease`` concurrency group, but that is belt-and-
suspenders: the PyPI lookup alone already protects against duplicate
counters.

Outputs
=======
* ``new_versions``: pkg_id -> ``{cycle}.0rcN`` for every publishable
  package. Always covers the full publishable set — rc cuts do not
  honor a "selected" subset because every sibling needs to resolve.

* ``dep_pins``: normalized PyPI name -> ``>={cycle}.0rcN`` for every
  publishable package. Consumed by ``rewrite-pyproject-pre-release.py``,
  which stamps these into wheel ``Requires-Dist`` so every sibling is
  at the rc floor or newer.

Names in both maps are PEP 503 normalized so the rewrite step matches
``unique-sdk``, ``unique_sdk`` and ``Unique.SDK`` to the same entry.
"""

from __future__ import annotations

import argparse
import json
import re

# Reuse the helpers from the dev resolver — same PyPI lookup, same
# normalization, same package-config loader. Keeps the two resolvers in
# lockstep so a fix to either path benefits both.
from importlib import util as _import_util
from pathlib import Path

_DEV_RESOLVER_PATH = Path(__file__).resolve().with_name("resolve-dev-versions.py")
_spec = _import_util.spec_from_file_location("_resolve_dev", _DEV_RESOLVER_PATH)
assert _spec is not None and _spec.loader is not None
_resolve_dev = _import_util.module_from_spec(_spec)
_spec.loader.exec_module(_resolve_dev)
normalize = _resolve_dev.normalize
_fetch_versions = _resolve_dev._fetch_versions
_load_publishable = _resolve_dev._load_publishable
DEFAULT_PACKAGE_CONFIG = _resolve_dev.DEFAULT_PACKAGE_CONFIG
DEFAULT_PYPI_BASE_URL = _resolve_dev.DEFAULT_PYPI_BASE_URL

_CYCLE_RE = re.compile(r"^\d{4}\.\d{2}$")


def highest_rc_in_cycle(
    pypi_name: str,
    cycle: str,
    base_url: str,
    *,
    fetcher=_fetch_versions,
) -> int | None:
    """Return the highest ``N`` for which ``{cycle}.0rcN`` exists on PyPI."""
    pattern = re.compile(rf"^{re.escape(cycle)}\.0rc(\d+)$")
    ns = [
        int(m.group(1)) for v in fetcher(pypi_name, base_url) if (m := pattern.match(v))
    ]
    return max(ns) if ns else None


def resolve(
    *,
    cycle: str,
    publishable: list[dict],
    pypi_base_url: str,
    fetcher=_fetch_versions,
) -> tuple[dict[str, str], dict[str, str], int]:
    """Return ``(new_versions, dep_pins, rc_n)``.

    The shared ``rc_n`` is the global highest existing rc counter for
    the cycle plus one (or ``1`` when none exist). All publishable
    packages get the same version and the same exact pin.
    """
    if not _CYCLE_RE.match(cycle):
        raise SystemExit(f"invalid cycle: {cycle!r}")

    # Global max across every publishable package; one rc counter for the
    # whole cut so sibling ``>=`` pins always share the same floor.
    seen: list[int] = []
    for pkg in publishable:
        n = highest_rc_in_cycle(pkg["pypi_name"], cycle, pypi_base_url, fetcher=fetcher)
        if n is not None:
            seen.append(n)
    rc_n = (max(seen) + 1) if seen else 1
    version = f"{cycle}.0rc{rc_n}"

    new_versions: dict[str, str] = {}
    dep_pins: dict[str, str] = {}
    for pkg in publishable:
        new_versions[pkg["id"]] = version
        dep_pins[normalize(pkg["pypi_name"])] = f">={version}"

    return new_versions, dep_pins, rc_n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--package-config", default=str(DEFAULT_PACKAGE_CONFIG), type=Path
    )
    parser.add_argument("--pypi-base-url", default=DEFAULT_PYPI_BASE_URL)
    args = parser.parse_args(argv)

    publishable = _load_publishable(args.package_config)
    new_versions, dep_pins, rc_n = resolve(
        cycle=args.cycle,
        publishable=publishable,
        pypi_base_url=args.pypi_base_url,
    )
    version = f"{args.cycle}.0rc{rc_n}"

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Trailing newlines: the publish-rc workflow streams these into
    # GITHUB_OUTPUT as multiline values terminated by a delimiter on its
    # own line. Without the final ``\n``, ``cat file; echo DELIM`` emits
    # ``...}DELIM`` on one line and GitHub reports "Matching delimiter
    # not found".
    (out / "new_versions.json").write_text(json.dumps(new_versions, indent=2) + "\n")
    (out / "dep_pins.json").write_text(json.dumps(dep_pins, indent=2) + "\n")
    (out / "rc_version.txt").write_text(version + "\n")
    (out / "rc_n.txt").write_text(f"{rc_n}\n")

    print("### RC publish — version resolution\n")
    print(f"- Cycle: `{args.cycle}`")
    print(f"- RC version: `{version}` (counter: `rc{rc_n}`)")
    print(f"- Packages in cut: {len(publishable)}\n")
    print("| package | new version |\n| --- | --- |")
    for pid in sorted(new_versions):
        print(f"| `{pid}` | `{new_versions[pid]}` |")
    print("\n| dep | pinned to |\n| --- | --- |")
    for name in sorted(dep_pins):
        print(f"| `{name}` | `{dep_pins[name]}` |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
