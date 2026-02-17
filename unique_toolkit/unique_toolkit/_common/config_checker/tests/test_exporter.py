"""Tests for config exporter."""

import json
import os
import tempfile
from pathlib import Path

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

    class Config:
        env_prefix = "DB_"


def test_exporter_exports_simple_config():
    """Test exporting a simple config model."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(SimpleConfig)

    assert result == {"name": "test", "value": 42}


def test_exporter_exports_nested_config():
    """Test exporting nested config models."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(NestedConfig)

    assert result == {"simple": {"name": "test", "value": 42}, "enabled": True}


def test_exporter_handles_secret_str():
    """Test that SecretStr values are extracted."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(SecretConfig)

    assert result == {"api_key": "secret123", "token": "public"}


def test_exporter_handles_list_defaults():
    """Test exporting list defaults."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(ListConfig)

    assert result == {"items": ["a", "b"]}


def test_exporter_handles_dict_defaults():
    """Test exporting dict defaults."""
    exporter = ConfigExporter()

    result = exporter.export_defaults(DictConfig)

    assert result == {"metadata": {"version": "1.0"}}


def test_exporter_warns_on_environment_variables():
    """Test that exporter warns when env vars are set."""
    exporter = ConfigExporter()

    # Set an env var
    os.environ["DB_HOST"] = "remote.db"

    try:
        result = exporter.export_defaults(EnvironmentSettings)

        # Should still export code defaults
        assert result["db_host"] == "localhost"
        assert result["db_port"] == 5432

        # Should have warnings
        assert len(exporter.warnings) > 0
        assert any("DB_HOST" in w.var_name for w in exporter.warnings)

    finally:
        del os.environ["DB_HOST"]


def test_exporter_export_all_to_directory():
    """Test exporting multiple configs to a directory."""
    exporter = ConfigExporter()

    entries = [
        ConfigEntry("SimpleConfig", SimpleConfig, "auto_discovery"),
        ConfigEntry("NestedConfig", NestedConfig, "auto_discovery"),
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


def test_exporter_handles_instantiation_errors():
    """Test that exporter handles models that fail to instantiate."""

    class BadConfig(BaseModel):
        required_field: str  # No default

    exporter = ConfigExporter()
    entries = [ConfigEntry("BadConfig", BadConfig, "auto_discovery")]

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = exporter.export_all(entries, Path(tmpdir))

        assert manifest.exported_count == 0
        assert manifest.skipped_count == 1


def test_exporter_tracks_config_file_paths():
    """Test that exporter tracks output file paths in manifest."""
    exporter = ConfigExporter()

    entries = [ConfigEntry("SimpleConfig", SimpleConfig, "auto_discovery")]

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = exporter.export_all(entries, Path(tmpdir))

        assert "SimpleConfig" in manifest.config_files
        assert manifest.config_files["SimpleConfig"].endswith("SimpleConfig.json")
