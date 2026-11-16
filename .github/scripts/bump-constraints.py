#!/usr/bin/env python3
"""Raise root constraint-dependencies floors. Missing versions come from uv audit; existing floors are never lowered."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

_PACKAGE_LINE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\s*>=\s*(?P<version>\S+))?$"
)
_AUDIT_HEADER = re.compile(r"^(\S+) \S+ has \d+ known vulnerabilit")
_FIXED_IN = re.compile(r"^\s*Fixed in:\s*(.+?)\s*$")
_VERSION_TOKEN = re.compile(r"\d+[0-9A-Za-z._!-]*")
_REQ_LINE = re.compile(r'^(\s*)"([^"]+)"(,?)(\s*(?:#.*)?)$')


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
        name = canonicalize_name(match.group("name"))
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
    target = canonicalize_name(name)
    versions: list[str] = []
    in_block = False
    for line in audit_text.splitlines():
        header = _AUDIT_HEADER.match(line)
        if header:
            in_block = canonicalize_name(header.group(1)) == target
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
            current = canonicalize_name(header.group(1))
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


def _parse_req(spec: str) -> Requirement:
    try:
        return Requirement(spec)
    except InvalidRequirement as exc:
        raise BumpError(f"Invalid constraint {spec!r}: {exc}") from exc


def _bound(spec: str | None) -> str | None:
    if spec is None:
        return None
    floors = [s.version for s in _parse_req(spec).specifier if s.operator == ">="]
    return _highest(floors) if floors else None


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
    return canonicalize_name(_parse_req(spec).name)


def _rewrite_spec(spec: str, floor: str) -> str:
    req = _parse_req(spec)
    name = canonicalize_name(req.name)
    extras = f"[{','.join(sorted(req.extras))}]" if req.extras else ""
    others = [str(s) for s in req.specifier if s.operator != ">="]
    specs = ",".join([f">={floor}", *others])
    marker = f"; {spec.split(';', 1)[1].strip()}" if ";" in spec else ""
    return f"{name}{extras}{specs}{marker}"


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
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].split("#", 1)[0].strip() == "]"
        ),
        None,
    )
    if end is None:
        raise BumpError("constraint-dependencies block is not closed")
    return start, end


def _comment_start(lines: list[str], index: int, block_start: int) -> int:
    while index > block_start + 1 and lines[index - 1].strip().startswith("#"):
        index -= 1
    return index


def patch_constraints(text: str, updates: dict[str, str]) -> str:
    lines = text.splitlines(keepends=True)
    start, end = _constraint_span(lines)
    canonical = {canonicalize_name(k): v for k, v in updates.items()}
    seen: set[str] = set()
    for index in range(start + 1, end):
        match = _REQ_LINE.match(lines[index].rstrip("\r\n"))
        if match is None:
            continue
        indent, spec, comma, tail = match.groups()
        name = _spec_name(spec)
        if name not in canonical:
            continue
        seen.add(name)
        newline = "\n" if lines[index].endswith("\n") else ""
        rewritten_spec = _rewrite_spec(spec, canonical[name])
        lines[index] = f'{indent}"{rewritten_spec}"{comma}{tail}{newline}'

    for name in sorted(set(canonical) - seen):
        inserted = False
        end = _constraint_span(lines)[1]
        for index in range(start + 1, end):
            match = _REQ_LINE.match(lines[index].rstrip("\r\n"))
            if match is None or _spec_name(match.group(2)) <= name:
                continue
            at = _comment_start(lines, index, start)
            _ensure_comma(lines, at, start)
            lines.insert(at, f'    "{name}>={canonical[name]}",\n')
            inserted = True
            break
        if not inserted:
            end = _constraint_span(lines)[1]
            _ensure_comma(lines, end, start)
            lines.insert(end, f'    "{name}>={canonical[name]}",\n')
    return "".join(lines)


def _ensure_comma(lines: list[str], index: int, block_start: int) -> None:
    previous = index - 1
    while previous > block_start and (
        not lines[previous].strip() or lines[previous].lstrip().startswith("#")
    ):
        previous -= 1
    if previous <= block_start:
        return
    match = _REQ_LINE.match(lines[previous].rstrip("\r\n"))
    if match is None or match.group(3):
        return
    indent, spec, _, tail = match.groups()
    newline = "\n" if lines[previous].endswith("\n") else ""
    lines[previous] = f'{indent}"{spec}",{tail}{newline}'


def locked_versions(lock_text: str, name: str) -> list[str]:
    try:
        packages = tomllib.loads(lock_text).get("package", [])
    except tomllib.TOMLDecodeError as exc:
        raise BumpError(f"Invalid uv.lock: {exc}") from exc
    target = canonicalize_name(name)
    return [
        str(pkg["version"])
        for pkg in packages
        if canonicalize_name(str(pkg.get("name", ""))) == target and "version" in pkg
    ]


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
    floors: dict[str, str] = {}
    notes: dict[str, str] = {}
    for name, explicit in requests:
        prev_spec = existing[name]
        prev_floor = _bound(prev_spec)
        floor, note = resolve_floor(name, explicit, audit_text, prev_spec)
        floors[name] = floor
        notes[name] = note
        if prev_floor is None or Version(floor) > Version(prev_floor):
            updates[name] = floor
    rewritten = patch_constraints(pyproject, updates) if updates else pyproject
    bumps: list[dict[str, object]] = []
    for name, _explicit in requests:
        bumps.append(
            {
                "name": name,
                "previous": existing[name],
                "floor": floors[name],
                "audit": notes[name],
                "changed": name in updates,
                "locked": None,
            }
        )
    return rewritten, bumps


def _existing_specs(pyproject: str, names: list[str]) -> dict[str, str | None]:
    lines = pyproject.splitlines(keepends=True)
    start, end = _constraint_span(lines)
    found: dict[str, str | None] = {name: None for name in names}
    for index in range(start + 1, end):
        match = _REQ_LINE.match(lines[index].rstrip("\r\n"))
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
