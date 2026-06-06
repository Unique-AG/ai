"""Validate tangled doc examples: PEP 723 metadata, syntax, and static imports.

Run from the repository root after syncing workspace packages:

    uv sync --locked --package unique_sdk --package unique_toolkit
    uv sync --package unique_toolkit --extra langchain
    uv run python unique_toolkit/scripts/validate_doc_examples.py
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = TOOLKIT_ROOT / "docs" / "examples_from_docs"


def _script_block_count(source: str) -> int:
    return source.count("# /// script")


def _validate_metadata(path: Path, source: str) -> list[str]:
    errors: list[str] = []
    count = _script_block_count(source)
    if count != 1:
        errors.append(
            f"{path.name}: expected exactly one '# /// script' block, found {count}"
        )
        return errors
    first_line = source.splitlines()[0] if source else ""
    if first_line != "# /// script":
        errors.append(
            f"{path.name}: '# /// script' must be on line 1 (found {first_line!r})"
        )
    return errors


def _top_level_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                modules.add(node.module.split(".")[0])
    return modules


def _validate_imports(path: Path, tree: ast.Module) -> list[str]:
    errors: list[str] = []
    for module_name in sorted(_top_level_modules(tree)):
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            errors.append(f"{path.name}: cannot import {module_name!r}: {exc}")
    return errors


def validate_examples(examples_dir: Path = EXAMPLES_DIR) -> int:
    if not examples_dir.is_dir():
        print(f"Examples directory not found: {examples_dir}", file=sys.stderr)
        return 1

    errors: list[str] = []
    scripts = sorted(examples_dir.glob("*.py"))
    if not scripts:
        print(f"No Python examples found in {examples_dir}", file=sys.stderr)
        return 1

    for path in scripts:
        source = path.read_text(encoding="utf-8")
        errors.extend(_validate_metadata(path, source))
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path.name}: syntax error: {exc}")
            continue
        errors.extend(_validate_imports(path, tree))

    if errors:
        print("Doc example validation failed:", file=sys.stderr)
        for message in errors:
            print(f"  - {message}", file=sys.stderr)
        return 1

    print(f"Validated {len(scripts)} examples in {examples_dir}")
    return 0


def main() -> None:
    sys.exit(validate_examples())


if __name__ == "__main__":
    main()
