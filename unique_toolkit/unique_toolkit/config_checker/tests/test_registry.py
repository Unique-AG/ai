"""Tests for config registry."""

import tempfile
from pathlib import Path

from pydantic import BaseModel

from unique_toolkit.config_checker.registry import ConfigRegistry


def test_registry_auto_discovers_config_classes():
    """Test that registry auto-discovers *Config and *Settings classes."""
    registry = ConfigRegistry()

    # Create a temporary config file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_dir = tmppath / "configs"
        config_dir.mkdir()

        # Write a simple config file
        config_file = config_dir / "config.py"
        config_file.write_text(
            """
from pydantic import BaseModel, BaseSettings

class TestConfig(BaseModel):
    value: int = 42

class TestSettings(BaseSettings):
    host: str = "localhost"
"""
        )

        entries = registry.discover_configs(tmppath)
        assert len(entries) == 2
        assert any(e.name == "TestConfig" for e in entries)
        assert any(e.name == "TestSettings" for e in entries)
        assert all(e.source == "auto_discovery" for e in entries)


def test_registry_skips_configs_with_skip_marker():
    """Test that configs marked _skip_config_check are excluded."""
    registry = ConfigRegistry()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_dir = tmppath / "configs"
        config_dir.mkdir()

        config_file = config_dir / "config.py"
        config_file.write_text(
            """
from pydantic import BaseModel

class SkippedConfig(BaseModel):
    _skip_config_check = True
    value: int = 42
"""
        )

        entries = registry.discover_configs(tmppath)
        assert len(entries) == 0


def test_registry_explicit_registration_overrides_auto_discovery():
    """Test that explicit registration takes precedence."""
    registry = ConfigRegistry()

    # Create a simple model for testing
    class SimpleConfig(BaseModel):
        value: int = 42

    # Register explicitly
    registry.register_explicit(SimpleConfig, "SimpleConfig")

    # Get all configs
    all_configs = registry.get_all_configs(include_discovered=False)
    simple_entry = next((e for e in all_configs if e.name == "SimpleConfig"), None)

    assert simple_entry is not None
    assert simple_entry.source == "explicit_decorator"


def test_registry_returns_unique_configs_by_name():
    """Test that get_all_configs returns unique configs (no duplicates)."""
    registry = ConfigRegistry()

    # Create test models
    class SimpleConfig(BaseModel):
        value: int = 42

    class DatabaseSettings(BaseModel):
        host: str = "localhost"

    # Register them
    registry.register_explicit(SimpleConfig, "MyConfig")
    registry.register_explicit(DatabaseSettings, "MyOtherConfig")

    all_configs = registry.get_all_configs(include_discovered=False)

    assert len(all_configs) == 2
    names = {c.name for c in all_configs}
    assert names == {"MyConfig", "MyOtherConfig"}


def test_registry_handles_missing_package_path():
    """Test that registry handles non-existent paths gracefully."""
    registry = ConfigRegistry()

    entries = registry.discover_configs(Path("/nonexistent/path"))
    assert len(entries) == 0


def test_registry_discovers_nested_config_files():
    """Test that registry finds config.py files in nested directories."""
    registry = ConfigRegistry()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create nested structure
        (tmppath / "module1").mkdir()
        (tmppath / "module1" / "config.py").write_text(
            "from pydantic import BaseModel\nclass Module1Config(BaseModel):\n    value: int = 1"
        )

        (tmppath / "module2" / "submodule").mkdir(parents=True)
        (tmppath / "module2" / "submodule" / "config.py").write_text(
            "from pydantic import BaseModel\nclass Module2Config(BaseModel):\n    value: int = 2"
        )

        entries = registry.discover_configs(tmppath)
        names = {e.name for e in entries}
        assert "Module1Config" in names
        assert "Module2Config" in names


def test_registry_ignores_non_basemodel_classes():
    """Test that registry ignores classes that don't inherit from BaseModel."""
    registry = ConfigRegistry()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_dir = tmppath / "configs"
        config_dir.mkdir()

        config_file = config_dir / "config.py"
        config_file.write_text(
            """
class NotAModel:
    value = 42

class AlsoNotAModel:
    pass
"""
        )

        entries = registry.discover_configs(tmppath)
        assert len(entries) == 0


def test_registry_handles_import_errors_gracefully():
    """Test that registry handles files with import errors."""
    registry = ConfigRegistry()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_dir = tmppath / "configs"
        config_dir.mkdir()

        # Write invalid Python
        config_file = config_dir / "config.py"
        config_file.write_text("this is not valid python !!!")

        entries = registry.discover_configs(tmppath)
        assert len(entries) == 0
