#!/usr/bin/env python3
"""Reject bare httpx.AsyncClient construction inside Search Proxy."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (
    REPO_ROOT
    / "connectors/unique_search_proxy/unique_search_proxy_client"
    / "unique_search_proxy_client",
    REPO_ROOT
    / "connectors/unique_search_proxy/unique_search_proxy_core"
    / "unique_search_proxy_core",
)
ALLOWED_CONSTRUCTORS = {
    Path(
        "connectors/unique_search_proxy/unique_search_proxy_core/"
        "unique_search_proxy_core/http_client/client.py"
    )
}
EXCLUDED_PARTS = frozenset({"tests", "_generated", "__pycache__"})


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    column: int

    def render(self) -> str:
        return (
            f"{self.path.as_posix()}:{self.line}:{self.column}: "
            "construct httpx.AsyncClient through the shared HTTP client factory"
        )


class AsyncClientVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.httpx_aliases: set[str] = set()
        self.async_client_aliases: set[str] = set()
        self.partial_aliases: set[str] = set()
        self.violations: list[tuple[int, int]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for name in node.names:
            if name.name == "httpx":
                self.httpx_aliases.add(name.asname or name.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "httpx":
            for name in node.names:
                if name.name == "AsyncClient":
                    self.async_client_aliases.add(name.asname or name.name)
        if node.module == "functools":
            for name in node.names:
                if name.name == "partial":
                    self.partial_aliases.add(name.asname or name.name)
        self.generic_visit(node)

    def _is_async_client(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self.async_client_aliases
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "AsyncClient"
            and isinstance(node.value, ast.Name)
            and node.value.id in self.httpx_aliases
        )

    def visit_Call(self, node: ast.Call) -> None:
        is_constructor = self._is_async_client(node.func)
        is_partial_constructor = (
            isinstance(node.func, ast.Name)
            and node.func.id in self.partial_aliases
            and bool(node.args)
            and self._is_async_client(node.args[0])
        )
        if is_constructor or is_partial_constructor:
            self.violations.append((node.lineno, node.col_offset + 1))
        self.generic_visit(node)


def iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file():
            if path.suffix == ".py":
                yield path
            continue
        for candidate in path.rglob("*.py"):
            if not EXCLUDED_PARTS.intersection(candidate.parts):
                yield candidate


def scan(paths: Iterable[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in iter_python_files(paths):
        relative_path = path.resolve().relative_to(REPO_ROOT)
        if relative_path in ALLOWED_CONSTRUCTORS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = AsyncClientVisitor()
        visitor.visit(tree)
        violations.extend(
            Violation(relative_path, line, column)
            for line, column in visitor.violations
        )
    return sorted(violations, key=lambda item: (str(item.path), item.line))


def main(argv: list[str]) -> int:
    paths = tuple(Path(value).resolve() for value in argv) or SCAN_ROOTS
    violations = scan(paths)
    for violation in violations:
        print(violation.render(), file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
