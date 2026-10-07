"""Four architecture checks that Ruff and import-linter cannot express.

Keyword-only public functions, no private imports from outside the package,
no mutable module-level containers, and size and waiver budgets.

This module is the source of truth. A package that does not depend on
unique-toolkit copies it to ``scripts/lint_architecture.py``.
"""

from __future__ import annotations

import argparse
import ast
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple

POSITIONAL_MARKER = "arch-allow-positional:"
PRIVATE_IMPORT_MARKER = "arch-allow-private-import:"
_WAIVER_KEYS = {
    POSITIONAL_MARKER: "arch_allow_positional",
    PRIVATE_IMPORT_MARKER: "arch_allow_private_import",
}
_MUTABLE_CALLS = frozenset({"list", "dict", "set", "bytearray", "defaultdict"})
_METHOD_RECEIVERS = frozenset({"self", "cls"})


class Budgets(NamedTuple):
    default_max_lines: int
    ceilings: dict[str, int]
    waivers: dict[str, int]


class Violation(NamedTuple):
    path: Path
    line: int
    message: str


def find_violations(
    *,
    root: Path,
    package: str,
    budgets: Budgets,
    src: str = "src",
    budgets_path: Path = Path("arch_budgets.toml"),
) -> list[Violation]:
    violations: list[Violation] = []
    marker_counts = dict.fromkeys(
        (POSITIONAL_MARKER, PRIVATE_IMPORT_MARKER),
        0,
    )
    for path in _python_files(root=root, src=src):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source, filename=str(path))
        relative = path.relative_to(root)
        violations.extend(_check_functions(tree=tree, lines=lines, path=relative))
        violations.extend(
            _check_private_imports(
                tree=tree,
                lines=lines,
                path=relative,
                package=package,
            )
        )
        violations.extend(_check_mutable_state(tree=tree, path=relative))
        violations.extend(_check_file_size(lines=lines, path=relative, budgets=budgets))
        for line in lines:
            for marker in marker_counts:
                if marker in line:
                    marker_counts[marker] += 1
    for marker, count in marker_counts.items():
        key = _WAIVER_KEYS[marker]
        allowed = budgets.waivers.get(key, 0)
        if count > allowed:
            violations.append(
                Violation(
                    path=budgets_path,
                    line=1,
                    message=(
                        f"{count} {key} markers, budget is {allowed}. "
                        "Raise the waiver in the same change that needs it."
                    ),
                )
            )
    return violations


def load_budgets(path: Path) -> Budgets:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    file_size = data.get("file_size", {})
    ceilings = file_size.get("ceilings", {})
    waivers = data.get("waivers", {})
    return Budgets(
        default_max_lines=int(file_size.get("default_max_lines", 800)),
        ceilings={str(key): int(value) for key, value in ceilings.items()},
        waivers={str(key): int(value) for key, value in waivers.items()},
    )


def _python_files(*, root: Path, src: str) -> list[Path]:
    directory = root / src
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.rglob("*.py") if "__pycache__" not in path.parts
    )


def _signature_lineno(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    if node.decorator_list:
        return node.decorator_list[0].lineno
    return node.lineno


def _marked(*, lines: list[str], lineno: int, marker: str) -> bool:
    start = max(lineno - 2, 0)
    return any(marker in line for line in lines[start:lineno])


def _check_functions(
    *,
    tree: ast.AST,
    lines: list[str],
    path: Path,
) -> list[Violation]:
    violations: list[Violation] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            violations.extend(
                _check_signature(node=node, lines=lines, path=path, in_class=False)
            )
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    violations.extend(
                        _check_signature(
                            node=child,
                            lines=lines,
                            path=path,
                            in_class=True,
                        )
                    )
    return violations


def _check_signature(
    *,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    lines: list[str],
    path: Path,
    in_class: bool,
) -> list[Violation]:
    if node.name.startswith("_"):
        return []
    if _marked(lines=lines, lineno=_signature_lineno(node), marker=POSITIONAL_MARKER):
        return []
    positional = list(node.args.posonlyargs) + list(node.args.args)
    if node.args.vararg is not None:
        positional.append(node.args.vararg)
    if in_class and positional and positional[0].arg in _METHOD_RECEIVERS:
        positional = positional[1:]
    if not positional:
        return []
    names = ", ".join(arg.arg for arg in positional)
    return [
        Violation(
            path=path,
            line=node.lineno,
            message=(
                f"{node.name} takes positional arguments ({names}). "
                "Public functions take keyword arguments only."
            ),
        )
    ]


def _check_private_imports(
    *,
    tree: ast.AST,
    lines: list[str],
    path: Path,
    package: str,
) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            module = node.module or ""
            if _inside_package(module=module, package=package):
                continue
            private_module = any(
                _is_private(part) for part in module.split(".") if part
            )
            for alias in node.names:
                private_name = _is_private(alias.name)
                if not private_name and not private_module:
                    continue
                if _marked(
                    lines=lines,
                    lineno=node.lineno,
                    marker=PRIVATE_IMPORT_MARKER,
                ):
                    continue
                subject = (
                    f"private module {module}"
                    if private_module
                    else f"private name {alias.name} from {module}"
                )
                violations.append(
                    Violation(
                        path=path,
                        line=node.lineno,
                        message=(
                            f"imports {subject}. "
                            "Private names stay inside their package."
                        ),
                    )
                )
                if private_module:
                    break
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _inside_package(module=alias.name, package=package):
                    continue
                if not any(_is_private(part) for part in alias.name.split(".")):
                    continue
                if _marked(
                    lines=lines,
                    lineno=node.lineno,
                    marker=PRIVATE_IMPORT_MARKER,
                ):
                    continue
                violations.append(
                    Violation(
                        path=path,
                        line=node.lineno,
                        message=(
                            f"imports private module {alias.name}. "
                            "Private names stay inside their package."
                        ),
                    )
                )
    return violations


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _inside_package(*, module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


def _check_mutable_state(*, tree: ast.AST, path: Path) -> list[Violation]:
    violations: list[Violation] = []
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        value = node.value
        if value is not None and _is_mutable(value) and not _is_dunder_all(node):
            violations.append(
                Violation(
                    path=path,
                    line=node.lineno,
                    message=(
                        "module-level mutable container. Pass state in arguments."
                    ),
                )
            )
    return violations


def _is_dunder_all(node: ast.Assign | ast.AnnAssign) -> bool:
    if isinstance(node, ast.Assign):
        return all(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    return isinstance(node.target, ast.Name) and node.target.id == "__all__"


def _is_mutable(node: ast.expr) -> bool:
    if isinstance(
        node, ast.List | ast.Dict | ast.Set | ast.ListComp | ast.SetComp | ast.DictComp
    ):
        return True
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    else:
        name = ""
    return name in _MUTABLE_CALLS


def _check_file_size(
    *,
    lines: list[str],
    path: Path,
    budgets: Budgets,
) -> list[Violation]:
    key = path.as_posix()
    limit = budgets.ceilings.get(key, budgets.default_max_lines)
    count = len(lines)
    if count <= limit:
        return []
    return [
        Violation(
            path=path,
            line=count,
            message=f"{count} lines, budget is {limit}.",
        )
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path())
    parser.add_argument("--package", required=True)
    parser.add_argument("--src", default="src")
    parser.add_argument("--budgets", type=Path, default=Path("arch_budgets.toml"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    budgets_path = args.budgets
    if not budgets_path.is_absolute():
        budgets_path = root / budgets_path
    violations = find_violations(
        root=root,
        package=args.package,
        budgets=load_budgets(budgets_path),
        src=args.src,
        budgets_path=args.budgets,
    )
    for violation in violations:
        print(
            f"{violation.path}:{violation.line}: {violation.message}",
            file=sys.stderr,
        )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
