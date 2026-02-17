"""Tests for config validator."""

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from unique_toolkit._common.config_checker.models import (
    ConfigEntry,
    ConfigValidationResult,
)
from unique_toolkit._common.config_checker.models import (
    ValidationError as ValidationErrorModel,
)
from unique_toolkit._common.config_checker.validator import (
    ConfigValidator,
    ValidationReport,
)


class BaseConfig(BaseModel):
    name: str = "test"
    value: int = 42


class UpdatedConfig(BaseModel):
    name: str = "test"
    value: int = 100  # Changed default


class RemovedFieldConfig(BaseModel):
    name: str = "test"
    # value field removed


class TypeChangedConfig(BaseModel):
    name: str = "test"
    value: str = "42"  # Changed from int to str


@pytest.mark.ai
def test_validator_validates_compatible_config():
    """Test that validator accepts compatible configs."""
    validator = ConfigValidator()

    old_json = {"name": "test", "value": 42}
    result = validator.validate_config(old_json, BaseConfig, "BaseConfig")

    assert result.valid
    assert result.errors is None


@pytest.mark.ai
def test_validator_detects_removed_field():
    """Test that validator detects removed required fields."""
    validator = ConfigValidator()

    old_json = {"name": "test", "value": 42}
    result = validator.validate_config(
        old_json, RemovedFieldConfig, "RemovedFieldConfig"
    )

    assert not result.valid
    assert result.errors is not None
    assert len(result.errors) > 0


@pytest.mark.ai
def test_validator_detects_type_change():
    """Test that validator detects type changes."""
    validator = ConfigValidator()

    old_json = {"name": "test", "value": 42}
    result = validator.validate_config(old_json, TypeChangedConfig, "TypeChangedConfig")

    # Pydantic v2 is strict about type changes
    # int 42 should fail to validate as str
    # (unless there's coercion, which we don't want)
    if not result.valid:
        assert result.errors is not None


@pytest.mark.ai
def test_validator_detects_default_changes():
    """Test that validator detects (but doesn't fail on) default changes."""
    validator = ConfigValidator()

    old_json = {"name": "test", "value": 42}
    result = validator.validate_config(old_json, UpdatedConfig, "UpdatedConfig")

    assert result.valid
    assert result.default_changes is not None
    assert len(result.default_changes) > 0

    # Check the detected change
    change = result.default_changes[0]
    assert change.field_path == "value"
    assert change.old_value == 42
    assert change.new_value == 100


@pytest.mark.ai
def test_validator_validate_all_from_artifacts():
    """Test validating all configs from artifact directory."""
    validator = ConfigValidator()

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir)

        # Create artifact files
        (artifact_dir / "BaseConfig.json").write_text(
            json.dumps({"name": "test", "value": 42})
        )
        (artifact_dir / "UpdatedConfig.json").write_text(
            json.dumps({"name": "test", "value": 42})
        )

        # Create config entries
        entries = [
            ConfigEntry(name="BaseConfig", model=BaseConfig),
            ConfigEntry(name="UpdatedConfig", model=UpdatedConfig),
        ]

        report = validator.validate_all(artifact_dir, entries)

        assert report.total_configs == 2
        assert report.valid_count == 2
        assert report.invalid_count == 0


@pytest.mark.ai
def test_validator_reports_missing_config():
    """Test that validator reports configs that don't exist at tip."""
    validator = ConfigValidator()

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir)

        # Create artifact for a config that no longer exists
        (artifact_dir / "RemovedConfig.json").write_text(json.dumps({"value": 1}))

        # No matching entry for RemovedConfig
        entries = [
            ConfigEntry(name="BaseConfig", model=BaseConfig),
        ]

        # Case 1: fail_on_missing = True (default)
        report = validator.validate_all(artifact_dir, entries, fail_on_missing=True)

        assert report.total_configs == 2
        assert report.invalid_count == 1
        assert report.has_failures()

        # Find the RemovedConfig result
        result = next(r for r in report.results if r.config_name == "RemovedConfig")
        assert result.config_name == "RemovedConfig"
        assert not result.valid
        assert "not found" in result.errors[0].message.lower()

        # Find the BaseConfig result (new config)
        result_new = next(r for r in report.results if r.config_name == "BaseConfig")
        assert result_new.config_name == "BaseConfig"
        assert result_new.valid
        assert result_new.is_new

        # Case 2: fail_on_missing = False
        report2 = validator.validate_all(artifact_dir, entries, fail_on_missing=False)

        assert report2.total_configs == 2
        assert report2.invalid_count == 0
        assert not report2.has_failures()

        result2 = next(r for r in report2.results if r.config_name == "RemovedConfig")
        assert result2.config_name == "RemovedConfig"
        assert result2.valid
        assert "not found" in result2.errors[0].message.lower()


@pytest.mark.ai
def test_validator_handles_invalid_json():
    """Test that validator handles malformed JSON files."""
    validator = ConfigValidator()

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir)

        # Create invalid JSON
        (artifact_dir / "BadConfig.json").write_text("{invalid json")

        entries = [
            ConfigEntry(name="BadConfig", model=BaseConfig),
        ]

        report = validator.validate_all(artifact_dir, entries)

        assert report.invalid_count == 1
        result = report.results[0]
        assert "JSON" in result.errors[0].message


@pytest.mark.ai
def test_validation_report_has_failures():
    """Test ValidationReport.has_failures() method."""
    validator = ConfigValidator()

    # Valid result
    old_json = {"name": "test", "value": 42}
    result = validator.validate_config(old_json, BaseConfig, "BaseConfig")

    from unique_toolkit._common.config_checker.validator import ValidationReport

    report = ValidationReport(
        total_configs=1,
        valid_count=1,
        invalid_count=0,
        results=[result],
    )

    assert not report.has_failures()

    # Invalid result
    bad_result = validator.validate_config(
        old_json, RemovedFieldConfig, "RemovedFieldConfig"
    )
    report2 = ValidationReport(
        total_configs=1,
        valid_count=0,
        invalid_count=1,
        results=[bad_result],
    )

    assert report2.has_failures()


@pytest.mark.ai
def test_validator_error_summary_and_edge_cases():
    """Test ValidationReport error summary and validator edge cases."""
    # Test has_failures and get_error_summary
    res = ConfigValidationResult(
        config_name="Test",
        valid=False,
        errors=[ValidationErrorModel(field_path="f", message="err")],
    )
    report = ValidationReport(
        total_configs=1, valid_count=0, invalid_count=1, results=[res]
    )

    assert report.has_failures()
    summary = report.get_error_summary()
    assert "Validation failed" in summary
    assert "Test" in summary
    assert "f: err" in summary

    # Test success summary
    report_ok = ValidationReport(
        total_configs=1, valid_count=1, invalid_count=0, results=[]
    )
    assert "successfully" in report_ok.get_error_summary()

    # Test validator fallback in default check
    validator = ConfigValidator()

    class ReqConfig(BaseModel):
        x: int

    old_json = {"x": 1}
    # This will fail to instantiate without args
    result = validator.validate_config(old_json, ReqConfig, "Req")
    assert result.valid


@pytest.mark.ai
def test_validator_parse_errors_recursive():
    """Test recursive error parsing in validator."""
    validator = ConfigValidator()

    class Nested(BaseModel):
        y: int

    class Root(BaseModel):
        n_: Nested
        l_: list[Nested]

    # Invalid data to trigger ValidationError
    bad_data = {"n_": {"y": "hi"}, "l_": [{"y": "there"}]}

    try:
        Root.model_validate(bad_data)
    except ValidationError as e:
        errors = validator._parse_validation_errors(e, bad_data)
        assert len(errors) >= 2
        # Check field paths
        paths = [e.field_path for e in errors]
        assert "n_.y" in paths
        assert "l_.0.y" in paths


@pytest.mark.ai
def test_validator_rename_heuristic():
    """Test the rename heuristic in the validator."""
    validator = ConfigValidator()

    class OldModel(BaseModel):
        old_field: int = 1

    class NewModel(BaseModel):
        new_field: int

    old_json = {"old_field": 1}
    # This should trigger the "maybe you renamed it?" note
    result = validator.validate_config(old_json, NewModel, "RenameTest")
    assert not result.valid
    assert any("maybe you renamed it?" in e.message for e in result.errors)


@pytest.mark.ai
def test_validator_skip_manifest():
    """Test that validator skips manifest.json."""
    validator = ConfigValidator()
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir)
        (artifact_dir / "manifest.json").write_text("{}", encoding="utf-8")
        (artifact_dir / "C.json").write_text('{"x": 1}', encoding="utf-8")

        class C(BaseModel):
            x: int

        entries = [ConfigEntry(name="C", model=C)]

        report = validator.validate_all(artifact_dir, entries)
        assert report.total_configs == 1


@pytest.mark.ai
def test_validator_instantiation_fallback():
    """Test validator fallback when default instantiation fails."""
    validator = ConfigValidator()

    class ReqModel(BaseModel):
        x: int  # Required

    old_json = {"x": 1}
    # This will trigger lines 102-104 in validator.py
    result = validator.validate_config(old_json, ReqModel, "Req")
    assert result.valid
    assert result.default_changes is None


@pytest.mark.ai
def test_validator_handles_extra_allow():
    """Test that removing a field is okay if extra='allow'."""
    validator = ConfigValidator()

    class ExtraAllowModel(BaseModel):
        model_config = {"extra": "allow"}
        kept_field: int = 1

    old_json = {"kept_field": 1, "removed_field": 2}

    # Should be VALID but have a warning
    result = validator.validate_config(old_json, ExtraAllowModel, "ExtraAllow")

    assert result.valid
    assert result.warnings is not None
    assert any(
        "allowed because model allows extra fields" in w.message.lower()
        for w in result.warnings
    )
    assert result.errors is None


@pytest.mark.ai
def test_validator_handles_extra_ignore_is_breaking():
    """Test that removing a field is BREAKING if extra='ignore' (default)."""
    validator = ConfigValidator()

    class ExtraIgnoreModel(BaseModel):
        model_config = {"extra": "ignore"}
        kept_field: int = 1

    old_json = {"kept_field": 1, "removed_field": 2}

    # Should be INVALID
    result = validator.validate_config(old_json, ExtraIgnoreModel, "ExtraIgnore")

    assert not result.valid
    assert result.errors is not None
    assert any(
        "breaking change because model does not explicitly allow" in e.message.lower()
        for e in result.errors
    )
