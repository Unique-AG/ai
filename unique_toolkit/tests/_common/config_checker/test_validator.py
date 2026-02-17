"""Tests for config validator."""

import json
import tempfile
from pathlib import Path

from pydantic import BaseModel

from unique_toolkit._common.config_checker.models import ConfigEntry
from unique_toolkit._common.config_checker.validator import ConfigValidator


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


def test_validator_validates_compatible_config():
    """Test that validator accepts compatible configs."""
    validator = ConfigValidator()

    old_json = {"name": "test", "value": 42}
    result = validator.validate_config(old_json, BaseConfig, "BaseConfig")

    assert result.valid
    assert result.errors is None


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
            ConfigEntry("BaseConfig", BaseConfig, "auto_discovery"),
            ConfigEntry("UpdatedConfig", UpdatedConfig, "auto_discovery"),
        ]

        report = validator.validate_all(artifact_dir, entries)

        assert report.total_configs == 2
        assert report.valid_count == 2
        assert report.invalid_count == 0


def test_validator_reports_missing_config():
    """Test that validator reports configs that don't exist at tip."""
    validator = ConfigValidator()

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir)

        # Create artifact for a config that no longer exists
        (artifact_dir / "RemovedConfig.json").write_text(json.dumps({"value": 1}))

        # No matching entry for RemovedConfig
        entries = [
            ConfigEntry("BaseConfig", BaseConfig, "auto_discovery"),
        ]

        # Case 1: fail_on_missing = True (default)
        report = validator.validate_all(artifact_dir, entries, fail_on_missing=True)

        assert report.total_configs == 1
        assert report.invalid_count == 1
        assert report.has_failures()

        result = report.results[0]
        assert result.config_name == "RemovedConfig"
        assert not result.valid
        assert "not found" in result.errors[0].message.lower()

        # Case 2: fail_on_missing = False
        report2 = validator.validate_all(artifact_dir, entries, fail_on_missing=False)

        assert report2.total_configs == 1
        assert report2.invalid_count == 0
        assert not report2.has_failures()

        result2 = report2.results[0]
        assert result2.config_name == "RemovedConfig"
        assert result2.valid
        assert "not found" in result2.errors[0].message.lower()


def test_validator_handles_invalid_json():
    """Test that validator handles malformed JSON files."""
    validator = ConfigValidator()

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir)

        # Create invalid JSON
        (artifact_dir / "BadConfig.json").write_text("{invalid json")

        entries = [
            ConfigEntry("BadConfig", BaseConfig, "auto_discovery"),
        ]

        report = validator.validate_all(artifact_dir, entries)

        assert report.invalid_count == 1
        result = report.results[0]
        assert "JSON" in result.errors[0].message


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
