"""The four architecture checks fail when a package breaks them."""

from pathlib import Path

import pytest

from unique_toolkit.lint_architecture import (
    POSITIONAL_MARKER,
    Budgets,
    find_violations,
)

pytestmark = pytest.mark.ai

_POSITIONAL_WAIVER = "arch_allow_positional"

_BUDGETS = Budgets(default_max_lines=800, ceilings={}, waivers={})


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _messages(root: Path, budgets: Budgets = _BUDGETS) -> list[str]:
    return [
        item.message
        for item in find_violations(root=root, package="package_name", budgets=budgets)
    ]


def test_positional_public_function_fails(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        "def build(name: str) -> str:\n    return name\n",
    )
    messages = _messages(tmp_path)
    assert any("keyword arguments only" in message for message in messages)


def test_keyword_only_function_passes(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        "def build(*, name: str) -> str:\n    return name\n",
    )
    assert _messages(tmp_path) == []


def test_dunder_all_is_not_module_state(tmp_path: Path) -> None:
    _write(tmp_path, "src/package_name/work.py", '__all__ = ["Work"]\n')
    assert _messages(tmp_path) == []


def test_mutable_module_container_fails(tmp_path: Path) -> None:
    _write(tmp_path, "src/package_name/work.py", "ITEMS: list[str] = []\n")
    assert any("mutable container" in message for message in _messages(tmp_path))


def test_private_import_from_outside_fails(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        "from other_lib import _secret\n",
    )
    assert any("private name" in message for message in _messages(tmp_path))


def test_private_import_inside_the_package_passes(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        "from package_name.contract import _secret\n",
    )
    assert _messages(tmp_path) == []


def test_marker_counts_against_the_waiver_budget(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        f"# {POSITIONAL_MARKER} framework callback\ndef build(name: str) -> str:\n    return name\n",
    )
    messages = _messages(tmp_path)
    assert not any("keyword arguments only" in message for message in messages)
    assert any("budget is 0" in message for message in messages)

    allowed = Budgets(
        default_max_lines=800,
        ceilings={},
        waivers={_POSITIONAL_WAIVER: 1},
    )
    assert _messages(tmp_path, allowed) == []


def test_private_module_in_from_import_fails(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        "from other_lib._internal import thing\n",
    )
    assert any("private module" in message for message in _messages(tmp_path))


def test_marker_above_a_decorator_allows_positional(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        f"# {POSITIONAL_MARKER} framework callback\n"
        "@cache\n"
        "def build(name: str) -> str:\n"
        "    return name\n",
    )
    assert not any(
        "keyword arguments only" in message for message in _messages(tmp_path)
    )


def test_starargs_fail(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        "def run(*args: object) -> None:\n    del args\n",
    )
    assert any("keyword arguments only" in message for message in _messages(tmp_path))


def test_mutable_comprehension_and_defaultdict_fail(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        "ITEMS = [item for item in ()]\nCACHE = defaultdict(list)\n",
    )
    messages = _messages(tmp_path)
    assert sum("mutable container" in message for message in messages) == 2


def test_file_over_the_line_budget_fails(tmp_path: Path) -> None:
    _write(tmp_path, "src/package_name/work.py", "x = 1\n" * 5)
    budgets = Budgets(default_max_lines=2, ceilings={}, waivers={})
    assert any("budget is 2" in message for message in _messages(tmp_path, budgets))


def test_dunder_module_import_passes(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/package_name/work.py",
        "from __future__ import annotations\n",
    )
    assert _messages(tmp_path) == []
