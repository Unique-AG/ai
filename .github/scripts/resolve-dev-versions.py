#!/usr/bin/env python3
"""Resolve dev versions and cross-package dep pins for a dev publish run.

For each publishable AI package we answer two questions:

  * What is the highest ``{cycle}.0.devN`` already on PyPI, if any?
    (One per-package query, filtering the JSON release list by prefix.)
  * If nothing is in the cycle yet, what is the package's current
    on-disk version? That is the last stable floor — whatever was
    stamped into ``pyproject.toml`` by release-please or a manual
    release.

From that we produce:

  * ``new_versions``: for every selected package, ``{cycle}.0.dev(N+1)``
    (or ``dev0`` when nothing is in the cycle yet). Per-package
    contiguous counter, no gaps.

  * ``dep_pins``: for every publishable AI package, the PEP 440 spec
    suffix downstream wheels should use for it:
      - package is a sibling in this push   -> ``>=<new version>``
      - cycle already has a dev on PyPI     -> ``>={cycle}.0.dev<N>``
      - otherwise                           -> ``>=<pyproject version>``

Both maps key cross-package names by their PEP 503 normalized form so
``rewrite-pyproject-for-dev.py`` can match regardless of whether the
requirement spells the name with ``-``, ``_`` or ``.``.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKAGE_CONFIG = (
    REPO_ROOT
    / ".github"
    / "actions"
    / "get-packages-matrix"
    / "package_configuration.json"
)
DEFAULT_PYPI_BASE_URL = "https://pypi.org/pypi"

_CYCLE_RE = re.compile(r"^\d{4}\.\d{2}$")
_PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def normalize(name: str) -> str:
    # PEP 503 — unify "-", "_", ".".
    return re.sub(r"[-_.]+", "-", name).lower()


def _fetch_versions(pypi_name: str, base_url: str) -> list[str]:
    url = f"{base_url}/{pypi_name}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    return list((payload.get("releases") or {}).keys())


def highest_dev_in_cycle(
    pypi_name: str,
    cycle: str,
    base_url: str,
    *,
    fetcher=_fetch_versions,
) -> int | None:
    pattern = re.compile(rf"^{re.escape(cycle)}\.0\.dev(\d+)$")
    ns = [
        int(m.group(1)) for v in fetcher(pypi_name, base_url) if (m := pattern.match(v))
    ]
    return max(ns) if ns else None


def read_pyproject_version(pkg_dir: Path) -> str:
    pyproject = REPO_ROOT / pkg_dir / "pyproject.toml"
    m = _PYPROJECT_VERSION_RE.search(pyproject.read_text())
    if not m:
        raise SystemExit(f"{pyproject}: no [project].version")
    return m.group(1)


def resolve(
    *,
    cycle: str,
    selected_ids: list[str],
    publishable: list[dict],
    pypi_base_url: str,
    fetcher=_fetch_versions,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], str]:
    """Return (new_versions, dep_pins, all_current_versions, branch_suffix).

    ``all_current_versions`` maps every publishable package id to its best
    known version after this run:
      - just published in this push  → the new devN version
      - already has a dev in cycle   → the highest existing devN
      - no dev in cycle yet          → the on-disk pyproject.toml version

    ``branch_suffix`` is a compact string encoding the dev counters for all
    packages that have a dev version in the current cycle, ordered by their
    position in ``publishable``.  Example: ``tk-5-sdk-4-orch-3``.  It is
    empty when no package has a dev version in this cycle (fresh cycle, no
    publishes yet).
    """
    if not _CYCLE_RE.match(cycle):
        raise SystemExit(f"invalid cycle: {cycle!r}")

    selected = set(selected_ids)
    unknown = selected - {p["id"] for p in publishable}
    if unknown:
        raise SystemExit(f"unknown selected ids: {sorted(unknown)}")

    new_versions: dict[str, str] = {}
    dep_pins: dict[str, str] = {}
    all_current_versions: dict[str, str] = {}
    branch_parts: list[str] = []

    for pkg in publishable:
        pypi_name = pkg["pypi_name"]
        key = normalize(pypi_name)
        dev_n = highest_dev_in_cycle(pypi_name, cycle, pypi_base_url, fetcher=fetcher)
        if pkg["id"] in selected:
            next_n = 0 if dev_n is None else dev_n + 1
            version = f"{cycle}.0.dev{next_n}"
            new_versions[pkg["id"]] = version
            dep_pins[key] = f">={version}"
            all_current_versions[pkg["id"]] = version
            if sh := pkg.get("shorthand"):
                branch_parts.append(f"{sh}-{next_n}")
        elif dev_n is not None:
            version = f"{cycle}.0.dev{dev_n}"
            dep_pins[key] = f">={version}"
            all_current_versions[pkg["id"]] = version
            if sh := pkg.get("shorthand"):
                branch_parts.append(f"{sh}-{dev_n}")
        else:
            stable = read_pyproject_version(Path(pkg["dir"]))
            dep_pins[key] = f">={stable}"
            all_current_versions[pkg["id"]] = stable

    return new_versions, dep_pins, all_current_versions, "-".join(branch_parts)


def _load_publishable(config_path: Path) -> list[dict]:
    cfg = json.loads(config_path.read_text())
    return [e for e in cfg if not e.get("publish_skip") and e.get("pypi_name")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle", required=True)
    parser.add_argument("--selected-ids", required=True, help="JSON array")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--package-config", default=str(DEFAULT_PACKAGE_CONFIG), type=Path
    )
    parser.add_argument("--pypi-base-url", default=DEFAULT_PYPI_BASE_URL)
    args = parser.parse_args(argv)

    selected_ids = json.loads(args.selected_ids)
    if not (
        isinstance(selected_ids, list) and all(isinstance(s, str) for s in selected_ids)
    ):
        raise SystemExit("--selected-ids must be a JSON array of strings")

    publishable = _load_publishable(args.package_config)
    new_versions, dep_pins, all_current_versions, branch_suffix = resolve(
        cycle=args.cycle,
        selected_ids=selected_ids,
        publishable=publishable,
        pypi_base_url=args.pypi_base_url,
    )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Trailing newline is required: the publish-dev workflow streams these
    # files into GITHUB_OUTPUT as multiline values terminated by a delimiter
    # on its own line. Without the final `\n`, `cat file; echo DELIM` emits
    # `...}DELIM` on one line and GitHub reports "Matching delimiter not found".
    (out / "new_versions.json").write_text(json.dumps(new_versions, indent=2) + "\n")
    (out / "dep_pins.json").write_text(json.dumps(dep_pins, indent=2) + "\n")
    (out / "all_current_versions.json").write_text(
        json.dumps(all_current_versions, indent=2) + "\n"
    )
    # branch_suffix is a single-line value — no multiline delimiter needed.
    (out / "branch_suffix.txt").write_text(branch_suffix + "\n")

    print("### Dev publish — version resolution\n")
    print(f"- Cycle: `{args.cycle}`")
    print(
        f"- Selected ({len(selected_ids)}): `{', '.join(selected_ids) or '(none)'}`\n"
    )
    print("| package | new version |\n| --- | --- |")
    for pid, v in new_versions.items():
        print(f"| `{pid}` | `{v}` |")
    print("\n| dep | pinned to |\n| --- | --- |")
    for name in sorted(dep_pins):
        print(f"| `{name}` | `{dep_pins[name]}` |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
