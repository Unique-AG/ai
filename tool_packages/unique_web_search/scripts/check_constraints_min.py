"""
Validate that constraints-min.txt matches the minimum versions declared in pyproject.toml
for a specific baseline environment.

Baseline for this script:
  - Linux
  - Python 3.12

We intentionally only validate "easy" minimums:
  - exact pins (==)
  - lower bounds (>=)
  - compatible releases (~=) treated as a lower bound

We skip dependencies that do not provide a clear minimum in the specifier set.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

import tomllib
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version


_DEFAULT_ENV = cast(dict[str, str], cast(object, default_environment()))
BASELINE_ENV: dict[str, str] = {
    **_DEFAULT_ENV,
    "python_version": "3.12",
    "python_full_version": "3.12.0",
    "sys_platform": "linux",
    "platform_system": "Linux",
    # Often present in markers; keep deterministic.
    "platform_machine": "x86_64",
    # Important: avoid accidentally matching `extra == "..."` markers.
    "extra": "",
}


def _read_constraints_min(path: Path) -> dict[str, str]:
    """
    Parse constraints-min.txt containing lines like `name==1.2.3`.
    Ignores comments and blank lines.
    """
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9.+-]+)$", line)
        if not m:
            raise ValueError(
                f"Unsupported constraints-min line (expected `name==version`): {raw}"
            )
        out[canonicalize_name(m.group(1))] = m.group(2)
    return out


def _min_version_from_requirement(req: Requirement) -> str | None:
    """
    Extract a single minimum version if it is reasonably well-defined.

    Rules:
    - Exact `==` pin wins.
    - Otherwise, take the smallest `>=` or `~=` bound (if any).
    - If no lower bound exists, return None (skip).
    """
    equals = [s for s in req.specifier if s.operator == "=="]
    if equals:
        return str(Version(equals[0].version))

    lowers: list[Version] = []
    for s in req.specifier:
        if s.operator in (">=", "~="):
            lowers.append(Version(s.version))
    if lowers:
        return str(min(lowers))

    return None


def _iter_project_dependencies(pyproject: Mapping[str, object]) -> Iterable[str]:
    project_obj: object = pyproject.get("project", {})
    project: dict[str, object]
    if isinstance(project_obj, dict):
        project = cast(dict[str, object], project_obj)
    else:
        project = {}

    deps_obj: object = project.get("dependencies", [])
    if not isinstance(deps_obj, list):
        raise ValueError("[project].dependencies must be a list of strings")
    deps = cast(list[object], deps_obj)
    for dep in deps:
        if not isinstance(dep, str):
            raise ValueError("[project].dependencies must contain only strings")
        yield dep


def main() -> int:
    # Allow tests/CI to point the validator at a specific package directory.
    # Default: .../tool_packages/unique_web_search
    override_dir = os.environ.get("PACKAGE_DIR")
    package_dir = (
        Path(override_dir).expanduser().resolve()
        if override_dir
        else Path(__file__).resolve().parents[1]
    )
    pyproject_path = package_dir / "pyproject.toml"
    constraints_path = package_dir / "constraints-min.txt"

    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    constraints = _read_constraints_min(constraints_path)

    failures: list[str] = []

    for dep_str in _iter_project_dependencies(pyproject):
        req = Requirement(dep_str)

        # Only validate deps that apply to our baseline environment.
        if req.marker is not None and not req.marker.evaluate(BASELINE_ENV):
            continue

        expected_min = _min_version_from_requirement(req)
        if expected_min is None:
            # Can't determine a single "min" reliably for this dependency.
            continue

        name = canonicalize_name(req.name)
        got = constraints.get(name)
        if got is None:
            failures.append(
                f"{req.name}: missing from constraints-min.txt (expected min {expected_min}; spec: {dep_str})"
            )
            continue

        if got != expected_min:
            failures.append(
                f"{req.name}: constraints has {got}, but pyproject min is {expected_min} (spec: {dep_str})"
            )

    if failures:
        print("constraints-min.txt does not match pyproject minimums (for Linux + py312):")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("constraints-min.txt matches pyproject minimums (for Linux + py312), for checkable dependencies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


