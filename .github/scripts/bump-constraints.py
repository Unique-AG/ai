#!/usr/bin/env python3
"""Raise root constraint-dependencies floors. Missing versions come from uv audit; existing floors are never lowered."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from packaging.version import InvalidVersion, Version

_PACKAGE_LINE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\s*>=\s*(?P<version>\S+))?$"
)
_AUDIT_HEADER = re.compile(r"^(\S+) \S+ has \d+ known vulnerabilit")
_FIXED_IN = re.compile(r"^\s*Fixed in:\s*(.+?)\s*$")
_VERSION_TOKEN = re.compile(r"\d+[0-9A-Za-z._!-]*")
_REQ_LINE = re.compile(r'^(\s*)"([^"]+)"(,?)\s*$')
_LOCK_NAME = re.compile(r'^name = "([^"]+)"$')
_LOCK_VERSION = re.compile(r'^version = "([^"]+)"$')


class BumpError(Exception):
    pass


def parse_packages(text: str) -> list[tuple[str, str | None]]:
    found: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _PACKAGE_LINE.fullmatch(line)
        if match is None:
            raise BumpError(
                f"Expected 'name' or 'name>=version', got {line!r}. "
                "Other operators are not accepted."
            )
        name = match.group("name").lower()
        version = match.group("version")
        if version is not None:
            _require_version(version)
        if name in seen:
            raise BumpError(f"Duplicate package {name}")
        seen.add(name)
        found.append((name, version))
    if not found:
        raise BumpError("No packages given")
    return found


def _require_version(version: str) -> Version:
    try:
        return Version(version)
    except InvalidVersion as exc:
        raise BumpError(f"Not a version: {version}") from exc


def _versions_on_line(line: str) -> list[str]:
    fixed = _FIXED_IN.match(line)
    if fixed is None:
        return []
    versions: list[str] = []
    for token in _VERSION_TOKEN.findall(fixed.group(1)):
        try:
            Version(token)
        except InvalidVersion:
            continue
        versions.append(token)
    return versions


def fixed_versions(audit_text: str, name: str) -> list[str]:
    versions: list[str] = []
    in_block = False
    for line in audit_text.splitlines():
        header = _AUDIT_HEADER.match(line)
        if header:
            in_block = header.group(1).lower() == name.lower()
            continue
        if in_block:
            versions.extend(_versions_on_line(line))
    return versions


def audit_packages(audit_text: str) -> tuple[list[str], list[str]]:
    """Names uv audit can fix, then names it reports with no fixed version."""
    order: list[str] = []
    fixable: dict[str, bool] = {}
    current: str | None = None
    for line in audit_text.splitlines():
        header = _AUDIT_HEADER.match(line)
        if header:
            current = header.group(1).lower()
            if current not in fixable:
                order.append(current)
                fixable[current] = False
            continue
        if current is not None and _versions_on_line(line):
            fixable[current] = True
    fixed = [name for name in order if fixable[name]]
    unfixed = [name for name in order if not fixable[name]]
    return fixed, unfixed


def _highest(versions: list[str]) -> str:
    return max(versions, key=Version)


def _bound(spec: str | None) -> str | None:
    if spec is None or ">=" not in spec:
        return None
    version = spec.split(">=", 1)[1].strip().rstrip(",")
    _require_version(version)
    return version


def resolve_floor(
    name: str,
    explicit: str | None,
    audit_text: str,
    previous_spec: str | None,
) -> tuple[str, str]:
    published = fixed_versions(audit_text, name)
    if explicit is None:
        if not published:
            raise BumpError(
                f"{name}: uv audit has no fixed version. Pass an explicit name>=version floor."
            )
        floor = _highest(published)
        note = f"uv audit fixed in {floor}"
    else:
        floor = explicit
        note = (
            "uv audit fixed in " + ", ".join(published)
            if published
            else "uv audit does not list this package"
        )
    current = _bound(previous_spec)
    if current is not None and Version(current) >= Version(floor):
        return current, f"kept existing floor {current}; requested {floor}. {note}"
    return floor, note


def _spec_name(spec: str) -> str:
    return re.split(r"[<>=!~\[]", spec, maxsplit=1)[0].strip().lower()


def _constraint_span(lines: list[str]) -> tuple[int, int]:
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if line.startswith("constraint-dependencies")
        ),
        None,
    )
    if start is None:
        raise BumpError("constraint-dependencies block not found")
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].strip() == "]"), None
    )
    if end is None:
        raise BumpError("constraint-dependencies block is not closed")
    return start, end


def _comment_start(lines: list[str], index: int, block_start: int) -> int:
    while index > block_start + 1 and lines[index - 1].strip().startswith("#"):
        index -= 1
    return index


def patch_constraints(
    text: str, updates: dict[str, str]
) -> tuple[str, dict[str, str | None]]:
    """Return the rewritten file and the previous spec for each updated name."""
    lines = text.splitlines(keepends=True)
    start, end = _constraint_span(lines)
    previous: dict[str, str | None] = {name: None for name in updates}
    for index in range(start + 1, end):
        match = _REQ_LINE.match(lines[index].strip("\n"))
        if match is None:
            continue
        spec = match.group(2)
        name = _spec_name(spec)
        if name not in updates:
            continue
        previous[name] = spec
        indent, _, comma = match.groups()
        newline = "\n" if lines[index].endswith("\n") else ""
        lines[index] = f'{indent}"{name}>={updates[name]}"{comma}{newline}'

    missing = sorted(name for name, spec in previous.items() if spec is None)
    for name in missing:
        inserted = False
        end = _constraint_span(lines)[1]
        for index in range(start + 1, end):
            match = _REQ_LINE.match(lines[index].strip("\n"))
            if match is None or _spec_name(match.group(2)) <= name:
                continue
            at = _comment_start(lines, index, start)
            _ensure_comma(lines, at)
            lines.insert(at, f'    "{name}>={updates[name]}",\n')
            inserted = True
            break
        if not inserted:
            end = _constraint_span(lines)[1]
            _ensure_comma(lines, end)
            lines.insert(end, f'    "{name}>={updates[name]}",\n')
    return "".join(lines), previous


def _ensure_comma(lines: list[str], index: int) -> None:
    previous = index - 1
    while previous >= 0 and not lines[previous].strip():
        previous -= 1
    if previous < 0:
        return
    match = _REQ_LINE.match(lines[previous].strip("\n"))
    if match is None or match.group(3):
        return
    newline = "\n" if lines[previous].endswith("\n") else ""
    lines[previous] = f'{match.group(1)}"{match.group(2)}",{newline}'


def locked_versions(lock_text: str, name: str) -> list[str]:
    versions: list[str] = []
    current: str | None = None
    for line in lock_text.splitlines():
        stripped = line.strip()
        if stripped == "[[package]]":
            current = None
            continue
        named = _LOCK_NAME.match(stripped)
        if named:
            current = named.group(1).lower()
            continue
        version = _LOCK_VERSION.match(stripped)
        if version and current == name.lower():
            versions.append(version.group(1))
            current = None
    return versions


def check_locked(lock_text: str, bumps: list[dict[str, object]]) -> None:
    for bump in bumps:
        if not bump["changed"]:
            continue
        name = str(bump["name"])
        floor = str(bump["floor"])
        versions = locked_versions(lock_text, name)
        if not versions:
            raise BumpError(f"{name} is not in uv.lock after the lock")
        for version in versions:
            if Version(version) < Version(floor):
                raise BumpError(
                    f"{name} locked at {version}, below {floor}. "
                    "If that release is inside the 3-day exclude-newer window, "
                    "add an exclude-newer-package entry and rerun."
                )
        bump["locked"] = ", ".join(versions)


def plan(
    pyproject: str,
    packages_text: str,
    audit_text: str,
) -> tuple[str, list[dict[str, object]]]:
    if packages_text.strip():
        requests = parse_packages(packages_text)
    else:
        names, unfixed = audit_packages(audit_text)
        for name in unfixed:
            print(f"skip {name}: uv audit has no fixed version", file=sys.stderr)
        requests = [(name, None) for name in names]
    if not requests:
        return pyproject, []
    existing = _existing_specs(pyproject, [name for name, _ in requests])
    updates: dict[str, str] = {}
    notes: dict[str, str] = {}
    for name, explicit in requests:
        floor, note = resolve_floor(name, explicit, audit_text, existing[name])
        updates[name] = floor
        notes[name] = note
    rewritten, previous = patch_constraints(pyproject, updates)
    bumps: list[dict[str, object]] = []
    for name, _explicit in requests:
        spec = f"{name}>={updates[name]}"
        bumps.append(
            {
                "name": name,
                "previous": previous[name],
                "floor": updates[name],
                "audit": notes[name],
                "changed": previous[name] != spec,
                "locked": None,
            }
        )
    return rewritten, bumps


def _existing_specs(pyproject: str, names: list[str]) -> dict[str, str | None]:
    lines = pyproject.splitlines(keepends=True)
    start, end = _constraint_span(lines)
    found: dict[str, str | None] = {name: None for name in names}
    for index in range(start + 1, end):
        match = _REQ_LINE.match(lines[index].strip("\n"))
        if match is None:
            continue
        spec = match.group(2)
        name = _spec_name(spec)
        if name in found:
            found[name] = spec
    return found


def apply_files(
    pyproject_path: Path,
    packages_text: str,
    audit_text: str,
    manifest_path: Path,
) -> dict[str, object]:
    rewritten, bumps = plan(pyproject_path.read_text(), packages_text, audit_text)
    changed = any(bump["changed"] for bump in bumps)
    if changed:
        pyproject_path.write_text(rewritten)
    manifest = {"changed": changed, "bumps": bumps}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def _die(exc: BumpError) -> None:
    print(f"error: {exc}", file=sys.stderr)
    raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--pyproject", type=Path, required=True)
    apply_parser.add_argument("--packages", type=Path, required=True)
    apply_parser.add_argument("--audit", type=Path, required=True)
    apply_parser.add_argument("--manifest", type=Path, required=True)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--lock", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "apply":
            apply_files(
                args.pyproject,
                args.packages.read_text(),
                args.audit.read_text(),
                args.manifest,
            )
            return
        manifest = json.loads(args.manifest.read_text())
        check_locked(args.lock.read_text(), manifest["bumps"])
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    except BumpError as exc:
        _die(exc)


if __name__ == "__main__":
    main()
