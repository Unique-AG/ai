"""Tests for config exporter."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings

from unique_toolkit._common.config_checker.exporter import ConfigExporter
from unique_toolkit._common.config_checker.models import ConfigEntry


class SimpleConfig(BaseModel):
    name: str = "test"
    value: int = 42


class NestedConfig(BaseModel):
    simple: SimpleConfig = Field(default_factory=SimpleConfig)
    enabled: bool = True


class SecretConfig(BaseModel):
    api_key: SecretStr = SecretStr("secret123")
    token: str = "public"


class ListConfig(BaseModel):
    items: list[str] = Field(default_factory=lambda: ["a", "b"])


class DictConfig(BaseModel):
    metadata: dict[str, str] = Field(default_factory=lambda: {"version": "1.0"})


class EnvironmentSettings(BaseSettings):
    """Settings that read from environment."""

    db_host: str = "localhost"
    db_port: int = 5432

    model_config = {"env_prefix": "DB_"}


@pytest.mark.ai
def test_exporter_exports_simple_config():
    """Test exporting a simple config model."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(SimpleConfig)

    assert result == {"name": "test", "value": 42}


@pytest.mark.ai
def test_exporter_exports_nested_config():
    """Test exporting nested config models."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(NestedConfig)

    assert result == {"simple": {"name": "test", "value": 42}, "enabled": True}


@pytest.mark.ai
def test_exporter_handles_secret_str():
    """Test that SecretStr values are hashed for security (not plain-text or obfuscated)."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(SecretConfig)

    # Should NOT be the actual value
    assert result["api_key"] != "secret123"
    # Should NOT be '**********'
    assert result["api_key"] != "**********"
    # Should be a hash
    assert result["api_key"].startswith("secret_hash:sha256:")

    # Verify deterministic hashing
    import hashlib

    expected_hash = hashlib.sha256(b"secret123").hexdigest()
    assert result["api_key"] == f"secret_hash:sha256:{expected_hash}"


@pytest.mark.ai
def test_exporter_handles_list_defaults():
    """Test exporting list defaults."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(ListConfig)

    assert result == {"items": ["a", "b"]}


@pytest.mark.ai
def test_exporter_handles_dict_defaults():
    """Test exporting dict defaults."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(DictConfig)

    assert result == {"metadata": {"version": "1.0"}}


@pytest.mark.ai
def test_exporter_special_types():
    """Test serialization of Path and Enum."""
    from enum import Enum

    class Status(Enum):
        ACTIVE = "active"

    class SpecialConfig(BaseModel):
        path: Path = Path("/tmp")
        status: Status = Status.ACTIVE
        empty_secret: SecretStr = SecretStr("")

    exporter = ConfigExporter()
    result = exporter.export_defaults(SpecialConfig)

    assert result["path"] == "/tmp"
    assert result["status"] == "active"
    assert result["empty_secret"] == ""


@pytest.mark.ai
def test_exporter_instantiation_error():
    """Test error handling during instantiation."""

    class BrokenConfig(BaseModel):
        @classmethod
        def model_construct(cls, _fields_set=None, **values):
            raise ValueError("Broken")

    exporter = ConfigExporter()
    with pytest.raises(ValueError, match="Broken"):
        exporter.export_defaults(BrokenConfig)


@pytest.mark.ai
def test_exporter_export_all_error_handling():
    """Test that export_all continues on individual config errors."""
    exporter = ConfigExporter()

    class BrokenConfig(BaseModel):
        def __init__(self, **data):
            if (
                not data
            ):  # model_construct bypasses this, but let's force an error if possible
                raise ValueError("Broken")

    # Force error by mocking export_defaults
    with patch.object(exporter, "export_defaults", side_effect=ValueError("Forced")):
        entries = [ConfigEntry(name="Broken", model=BrokenConfig)]
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = exporter.export_all(entries, Path(tmpdir))
            assert manifest.skipped_count == 1
            assert manifest.exported_count == 0


@pytest.mark.ai
def test_exporter_env_var_field_name():
    """Test environment variable detection by field name."""

    class EnvFieldConfig(BaseSettings):
        my_field: str = "default"
        model_config = {"env_prefix": "PREFIX_"}

    exporter = ConfigExporter()
    os.environ["MY_FIELD"] = "env_val"
    try:
        exporter.export_defaults(EnvFieldConfig)
        assert "MY_FIELD" in exporter.detected_env_vars
    finally:
        del os.environ["MY_FIELD"]


@pytest.mark.ai
def test_exporter_warns_on_environment_var():
    """Test that exporter warns when env vars are set."""
    exporter = ConfigExporter()

    # Set an env var that matches prefix
    os.environ["DB_HOST"] = "remote.db"
    # Set an env var that matches field name (even without prefix)
    os.environ["DB_PORT"] = "9999"

    try:
        # Need to use export_all to see consolidated warnings
        entries = [
            ConfigEntry(
                name="EnvironmentSettings",
                model=EnvironmentSettings,
            )
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = exporter.export_all(entries, Path(tmpdir))

            # Should have exactly one consolidated warning
            assert len(manifest.warnings) == 1
            warning = manifest.warnings[0]
            assert "DB_HOST" in warning.message
            assert "DB_PORT" in warning.message
            assert "ignored" in warning.message

            # Check individual config export still ignores env
            with open(Path(tmpdir) / "EnvironmentSettings.json") as f:
                result = json.load(f)
            assert result["db_host"] == "localhost"
            assert result["db_port"] == 5432

    finally:
        if "DB_HOST" in os.environ:
            del os.environ["DB_HOST"]
        if "DB_PORT" in os.environ:
            del os.environ["DB_PORT"]


@pytest.mark.ai
def test_exporter_export_all_to_directory():
    """Test exporting multiple configs to a directory."""
    exporter = ConfigExporter()

    entries = [
        ConfigEntry(name="SimpleConfig", model=SimpleConfig),
        ConfigEntry(name="NestedConfig", model=NestedConfig),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = exporter.export_all(entries, Path(tmpdir))

        assert manifest.exported_count == 2
        assert manifest.skipped_count == 0

        # Check files exist
        simple_file = Path(tmpdir) / "SimpleConfig.json"
        nested_file = Path(tmpdir) / "NestedConfig.json"
        manifest_file = Path(tmpdir) / "manifest.json"

        assert simple_file.exists()
        assert nested_file.exists()
        assert manifest_file.exists()

        # Check content
        with open(simple_file) as f:
            simple_data = json.load(f)
        assert simple_data == {"name": "test", "value": 42}

        # Check manifest
        with open(manifest_file) as f:
            manifest_data = json.load(f)
        assert manifest_data["exported_count"] == 2


@pytest.mark.ai
def test_exporter_handles_required_fields():
    """Test that exporter handles models with required fields via model_construct."""

    class RequiredConfig(BaseModel):
        required_field: str  # No default

    exporter = ConfigExporter()
    entries = [ConfigEntry(name="RequiredConfig", model=RequiredConfig)]

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = exporter.export_all(entries, Path(tmpdir))

        # With model_construct, even required fields don't prevent export
        # (they will just be missing from the JSON)
        assert manifest.exported_count == 1
        assert manifest.skipped_count == 0

        # Check content
        with open(Path(tmpdir) / "RequiredConfig.json") as f:
            data = json.load(f)
        assert data == {}  # Empty because no fields have defaults


@pytest.mark.ai
def test_exporter_tracks_config_file_paths():
    """Test that exporter tracks output file paths in manifest."""
    exporter = ConfigExporter()

    entries = [ConfigEntry(name="SimpleConfig", model=SimpleConfig)]

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = exporter.export_all(entries, Path(tmpdir))

        assert "SimpleConfig" in manifest.config_files
        assert manifest.config_files["SimpleConfig"].endswith("SimpleConfig.json")
