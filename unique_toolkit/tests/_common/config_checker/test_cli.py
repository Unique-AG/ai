"""Tests for config checker CLI."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from unique_toolkit._common.config_checker.cli import (
    _generate_markdown_report,
    cli,
)
from unique_toolkit._common.config_checker.models import (
    ConfigValidationResult,
    DefaultChange,
    ValidationError,
)
from unique_toolkit._common.config_checker.registry import _clear_global_registry
from unique_toolkit._common.config_checker.validator import ValidationReport


@pytest.mark.verified
def test_main_module():
    """Test the __main__ module execution."""
    from unique_toolkit._common.config_checker import __main__

    # Just importing it doesn't execute the __name__ == "__main__" block
    # but it covers the import line.
    assert __main__.cli is not None


@pytest.mark.verified
def test_cli_export_command():
    """Integration test for 'export' CLI command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a package to scan
        pkg_path = Path(tmpdir) / "pkg_export"
        pkg_path.mkdir()
        module_name = "conf_export_unique_123"
        (pkg_path / f"{module_name}.py").write_text(
            "from unique_toolkit._common.config_checker import register_config\nfrom pydantic import BaseModel\n@register_config()\nclass CExport(BaseModel): x: int = 1",
            encoding="utf-8",
        )

        output_path = Path(tmpdir) / "out"

        # Clear registry and sys.modules before test
        _clear_global_registry()
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Run export
        result = runner.invoke(
            cli,
            ["export", "--package", str(pkg_path), "--output", str(output_path), "-v"],
        )

        assert result.exit_code == 0
        assert "Export complete" in result.output
        assert (output_path / "CExport.json").exists()
        assert (output_path / "manifest.json").exists()


@pytest.mark.verified
def test_cli_check_command():
    """Integration test for 'check' CLI command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        module_name = "conf_check_unique_456"
        artifacts = Path(tmpdir) / "artifacts"
        artifacts.mkdir()
        (artifacts / "CCheck.json").write_text('{"x": 1}', encoding="utf-8")

        pkg_path = Path(tmpdir) / "pkg_check"
        pkg_path.mkdir()
        (pkg_path / f"{module_name}.py").write_text(
            "from unique_toolkit._common.config_checker import register_config\nfrom pydantic import BaseModel\n@register_config()\nclass CCheck(BaseModel): x: int = 2",
            encoding="utf-8",
        )

        _clear_global_registry()
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Run check
        result = runner.invoke(
            cli,
            [
                "check",
                "--artifacts",
                str(artifacts),
                "--package",
                str(pkg_path),
                "--report-defaults",
            ],
        )

        assert result.exit_code == 0
        assert "Validation PASSED" in result.output
        assert "Default Value Changes" in result.output
        assert "`x`: 1 → 2" in result.output


@pytest.mark.verified
def test_cli_check_failure():
    """Test 'check' CLI command with breaking change."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        module_name = "conf_fail_unique_789"
        artifacts = Path(tmpdir) / "artifacts"
        artifacts.mkdir()
        (artifacts / "CFail.json").write_text('{"x": 1}', encoding="utf-8")

        pkg_path = Path(tmpdir) / "pkg_fail"
        pkg_path.mkdir()
        # Change x to string (breaking)
        (pkg_path / f"{module_name}.py").write_text(
            "from unique_toolkit._common.config_checker import register_config\nfrom pydantic import BaseModel\n@register_config()\nclass CFail(BaseModel): x: str",
            encoding="utf-8",
        )

        _clear_global_registry()
        if module_name in sys.modules:
            del sys.modules[module_name]

        result = runner.invoke(
            cli, ["check", "--artifacts", str(artifacts), "--package", str(pkg_path)]
        )

        assert result.exit_code == 1
        assert "Validation FAILED" in result.output


@pytest.mark.verified
def test_cli_check_failure_type_and_value_change():
    """Test 'check' CLI command with breaking change."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        module_name = "conf_fail_unique_789"
        artifacts = Path(tmpdir) / "artifacts"
        artifacts.mkdir()
        (artifacts / "CFail.json").write_text('{"x": 1}', encoding="utf-8")

        pkg_path = Path(tmpdir) / "pkg_fail"
        pkg_path.mkdir()
        # Change x to string (breaking)
        (pkg_path / f"{module_name}.py").write_text(
            "from unique_toolkit._common.config_checker import register_config\nfrom pydantic import BaseModel\n@register_config()\nclass CFail(BaseModel): x: str = '1'",
            encoding="utf-8",
        )

        _clear_global_registry()
        if module_name in sys.modules:
            del sys.modules[module_name]

        result = runner.invoke(
            cli, ["check", "--artifacts", str(artifacts), "--package", str(pkg_path)]
        )

        assert result.exit_code == 1
        assert "Validation FAILED" in result.output


@pytest.mark.verified
def test_generate_markdown_report_missing_configs():
    """Test markdown report generation for missing configs."""
    # Case 1: fail_on_missing = True
    res = ConfigValidationResult(
        config_name="Missing",
        valid=False,
        errors=[ValidationError(field_path="__root__", message="not found at tip")],
    )
    report = ValidationReport(
        total_configs=1, valid_count=0, invalid_count=1, results=[res]
    )

    md = _generate_markdown_report(report, fail_on_missing=True)
    assert "Missing Configurations (Failures)" in md
    assert "🔴" in md

    # Case 2: fail_on_missing = False
    res2 = ConfigValidationResult(
        config_name="Missing",
        valid=True,
        errors=[ValidationError(field_path="__root__", message="not found at tip")],
    )
    report2 = ValidationReport(
        total_configs=1, valid_count=1, invalid_count=0, results=[res2]
    )
    md2 = _generate_markdown_report(report2, fail_on_missing=False)
    assert "Missing Configurations (Warnings)" in md2
    assert "🟡" in md2


@pytest.mark.verified
def test_cli_output_report():
    """Test CLI with --output-report."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts = Path(tmpdir) / "artifacts"
        artifacts.mkdir()
        (artifacts / "C.json").write_text('{"x": 1}', encoding="utf-8")

        pkg_path = Path(tmpdir) / "pkg"
        pkg_path.mkdir()
        (pkg_path / "conf.py").write_text(
            "from unique_toolkit._common.config_checker import register_config\nfrom pydantic import BaseModel\n@register_config()\nclass C(BaseModel): x: int = 1",
            encoding="utf-8",
        )

        report_path = Path(tmpdir) / "report.md"
        _clear_global_registry()

        result = runner.invoke(
            cli,
            [
                "check",
                "--artifacts",
                str(artifacts),
                "--package",
                str(pkg_path),
                "--output-report",
                str(report_path),
            ],
        )
        assert result.exit_code == 0
        assert report_path.exists()
        assert "All Configurations Compatible" in report_path.read_text()


@pytest.mark.verified
def test_cli_main_run():
    """Test running the CLI via __main__."""
    import subprocess

    # Use sys.executable to run the current python
    # Add unique_toolkit to PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(os.getcwd()).resolve())

    # Just run --help to see if it works
    result = subprocess.run(
        [sys.executable, "-m", "unique_toolkit._common.config_checker", "--help"],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.getcwd(),
    )
    assert result.returncode == 0
    assert "Config compatibility checker CLI" in result.stdout


@pytest.mark.verified
def test_cli_no_configs_discovered():
    """Test export command when no configs are discovered."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "empty"
        pkg_path.mkdir()
        output_path = Path(tmpdir) / "out"

        _clear_global_registry()
        result = runner.invoke(
            cli, ["export", "--package", str(pkg_path), "--output", str(output_path)]
        )
        assert result.exit_code == 1
        assert "No configs discovered" in result.output


@pytest.mark.verified
def test_cli_complex_report():
    """Test markdown report generation with errors and changes."""
    res_err = ConfigValidationResult(
        config_name="ErrorConfig",
        valid=False,
        errors=[ValidationError(field_path="err", message="msg")],
    )
    res_change = ConfigValidationResult(
        config_name="ChangeConfig",
        valid=True,
        default_changes=[DefaultChange(field_path="val", old_value=1, new_value=2)],
    )
    report = ValidationReport(
        total_configs=2, valid_count=1, invalid_count=1, results=[res_err, res_change]
    )

    md = _generate_markdown_report(report, report_defaults=True)
    assert "Breaking Changes Detected" in md
    assert "Schema Validation Failures" in md
    assert "Default Value Changes" in md
    assert "`val`: 1 → 2" in md


@pytest.mark.verified
def test_exporter_warnings_in_cli():
    """Test CLI output when there are export warnings."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "pkg"
        pkg_path.mkdir()
        module_name = "conf_warn"
        (pkg_path / f"{module_name}.py").write_text(
            "from unique_toolkit._common.config_checker import register_config\nfrom pydantic_settings import BaseSettings\n@register_config()\nclass CWarn(BaseSettings): model_config={'env_prefix': 'CW_'}",
            encoding="utf-8",
        )

        _clear_global_registry()
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Set env var to trigger warning
        os.environ["CW_VAR"] = "1"
        try:
            result = runner.invoke(
                cli,
                [
                    "export",
                    "--package",
                    str(pkg_path),
                    "--output",
                    str(Path(tmpdir) / "out"),
                ],
            )
            assert "warning(s):" in result.output
        finally:
            del os.environ["CW_VAR"]


@pytest.mark.verified
def test_cli_skipped_configs_warning():
    """Test CLI output when some configs are skipped during export."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "pkg"
        pkg_path.mkdir()
        module_name = "conf_skip"
        (pkg_path / f"{module_name}.py").write_text(
            "from unique_toolkit._common.config_checker import register_config\nfrom pydantic import BaseModel\n@register_config()\nclass CSkip(BaseModel): x: int",
            encoding="utf-8",
        )

        _clear_global_registry()
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Force a failure in exporter.export_defaults to trigger "skipped" logic
        with patch(
            "unique_toolkit._common.config_checker.exporter.ConfigExporter.export_defaults",
            side_effect=ValueError("Forced"),
        ):
            result = runner.invoke(
                cli,
                [
                    "export",
                    "--package",
                    str(pkg_path),
                    "--output",
                    str(Path(tmpdir) / "out"),
                ],
            )
            assert "skipped" in result.output
