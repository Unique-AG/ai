import importlib.util
import textwrap
from pathlib import Path
from types import ModuleType

import pytest
from packaging.requirements import Requirement


@pytest.fixture
def validator_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "check_constraints_min.py"
    )
    spec = importlib.util.spec_from_file_location("check_constraints_min", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return module


def test_read_constraints_min_parses_and_canonicalizes(tmp_path, validator_module):
    p = tmp_path / "constraints-min.txt"
    p.write_text(
        textwrap.dedent(
            """
            # comment
            Requests==2.32.3
            typing-extensions==4.9.0
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    parsed = validator_module._read_constraints_min(p)
    assert parsed["requests"] == "2.32.3"
    assert parsed["typing-extensions"] == "4.9.0"


def test_read_constraints_min_rejects_non_pinned_line(tmp_path, validator_module):
    p = tmp_path / "constraints-min.txt"
    p.write_text("requests>=2.0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _ = validator_module._read_constraints_min(p)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("pydantic==2.12.3", "2.12.3"),
        ("pydantic>=2.12.3,<3", "2.12.3"),
        ("pydantic~=2.12.3", "2.12.3"),
        ("pydantic<3", None),
    ],
)
def test_min_version_from_requirement(spec, expected, validator_module):
    req = Requirement(spec)
    assert validator_module._min_version_from_requirement(req) == expected


def test_main_success_skips_non_baseline_markers(tmp_path, monkeypatch, validator_module):
    # Create a fake package dir with pyproject + constraints.
    (tmp_path / "scripts").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "x"
            version = "0.0.0"
            dependencies = [
              "pydantic>=2.12.3,<3",
              "tzdata>=1.0; platform_system == 'Windows'",  # should be skipped on linux baseline
              "something<2",  # no clear min => skipped
            ]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "constraints-min.txt").write_text(
        "pydantic==2.12.3\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("PACKAGE_DIR", str(tmp_path))
    assert validator_module.main() == 0


def test_main_fails_on_missing_min_pin(tmp_path, monkeypatch, validator_module, capsys):
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "x"
            version = "0.0.0"
            dependencies = ["pydantic>=2.12.3,<3"]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "constraints-min.txt").write_text("", encoding="utf-8")

    monkeypatch.setenv("PACKAGE_DIR", str(tmp_path))
    rc = validator_module.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "missing from constraints-min.txt" in out


def test_main_fails_on_wrong_min_pin(tmp_path, monkeypatch, validator_module, capsys):
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "x"
            version = "0.0.0"
            dependencies = ["pydantic>=2.12.3,<3"]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "constraints-min.txt").write_text("pydantic==2.12.2\n", encoding="utf-8")

    monkeypatch.setenv("PACKAGE_DIR", str(tmp_path))
    rc = validator_module.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "constraints has 2.12.2" in out


