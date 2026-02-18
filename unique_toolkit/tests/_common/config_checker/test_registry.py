"""Tests for config registry."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from unique_toolkit._common.config_checker.registry import (
    ConfigRegistry,
    _clear_global_registry,
    register_config,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the global registry before each test."""
    _clear_global_registry()
    yield


class SimpleConfig(BaseModel):
    value: int = 42


class AnotherConfig(BaseModel):
    name: str = "test"


@pytest.mark.verified
def test_registry_explicit_registration():
    """Test that configs must be explicitly registered."""
    registry = ConfigRegistry()

    # Register explicitly
    registry.register_explicit(SimpleConfig, "SimpleConfig")

    # Get all configs
    all_configs = registry.get_all_configs()

    assert len(all_configs) == 1
    assert all_configs[0].name == "SimpleConfig"
    assert all_configs[0].source == "explicit"


@pytest.mark.verified
def test_registry_decorator_registration():
    """Test that @register_config decorator works."""

    @register_config(name="custom_name")
    class MyConfig(BaseModel):
        value: int = 1

    registry = ConfigRegistry()
    all_configs = registry.get_all_configs()

    # Should find the decorator-registered config
    assert len(all_configs) == 1
    assert all_configs[0].name == "custom_name"
    assert all_configs[0].model == MyConfig


@pytest.mark.verified
def test_registry_decorator_with_auto_name():
    """Test that @register_config works without explicit name."""

    @register_config()
    class AutoNamedConfig(BaseModel):
        value: str = "test"

    registry = ConfigRegistry()
    all_configs = registry.get_all_configs()

    # Should use class name as config name
    assert len(all_configs) == 1
    assert all_configs[0].name == "AutoNamedConfig"
    assert all_configs[0].model == AutoNamedConfig


@pytest.mark.verified
def test_registry_multiple_explicit_configs():
    """Test registering multiple explicit configs."""
    registry = ConfigRegistry()

    registry.register_explicit(SimpleConfig, "Config1")
    registry.register_explicit(AnotherConfig, "Config2")

    all_configs = registry.get_all_configs()

    assert len(all_configs) == 2
    assert all_configs[0].name == "Config1"
    assert all_configs[0].model == SimpleConfig
    assert all_configs[1].name == "Config2"
    assert all_configs[1].model == AnotherConfig


@pytest.mark.verified
def test_registry_explicit_takes_precedence():
    """Test that explicit registration is used in get_all_configs."""
    registry = ConfigRegistry()

    # Register the same config twice (shouldn't happen, but should be safe)
    registry.register_explicit(SimpleConfig, "MyConfig")
    registry.register_explicit(AnotherConfig, "MyConfig")  # Overwrite

    all_configs = registry.get_all_configs()

    # Should have only one entry (the last one wins)
    assert len(all_configs) == 1
    assert all_configs[0].name == "MyConfig"
    assert all_configs[0].model == AnotherConfig


@pytest.mark.verified
def test_registry_handles_missing_package_path():
    """Test that registry handles non-existent paths gracefully."""
    registry = ConfigRegistry()

    entries = registry.discover_configs("/nonexistent/path")
    assert len(entries) == 0


@pytest.mark.verified
def test_registry_discovery_complex():
    """Test complex discovery scenarios in registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Test src directory detection
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        pkg_dir = src_dir / "my_pkg"
        pkg_dir.mkdir()

        (pkg_dir / "config.py").write_text(
            "@register_config()\nclass MyConfig(BaseModel): pass", encoding="utf-8"
        )
        (pkg_dir / "skip.txt").write_text("not python", encoding="utf-8")
        (pkg_dir / ".hidden.py").write_text("hidden", encoding="utf-8")

        # Mock register_config to avoid actual registration in global registry
        with patch("unique_toolkit._common.config_checker.registry.register_config"):
            registry = ConfigRegistry()
            # Need to mock sys.path to avoid polluting it
            with patch("sys.path", sys.path[:]):
                registry.discover_configs(tmp_path)
                assert str(src_dir.resolve()) in [
                    str(Path(p).resolve()) for p in sys.path
                ]
                assert str(pkg_dir.resolve()) not in [  # if src, use src
                    str(Path(p).resolve()) for p in sys.path
                ]


@pytest.mark.verified
def test_registry_discovery_skips_non_config_files():
    """Test that discovery skips files without register_config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        (pkg_dir / "registered_config.py").write_text(
            "@register_config()\nclass C1(BaseModel): pass", encoding="utf-8"
        )
        (pkg_dir / "other.py").write_text("class C2(BaseModel): pass", encoding="utf-8")

        registry = ConfigRegistry()
        with patch("importlib.util.spec_from_file_location") as mock_spec:
            with patch("sys.path", sys.path[:]):
                registry.discover_configs(tmp_path)

                # Should only be called for config.py, not other.py
                called_files = [call.args[1] for call in mock_spec.call_args_list]
                assert any("registered_config.py" in str(f) for f in called_files)
                assert not any("other.py" in str(f) for f in called_files)


@pytest.mark.verified
def test_registry_load_from_package():
    """Test load_from_package method in registry."""
    registry = ConfigRegistry()
    with tempfile.TemporaryDirectory() as tmpdir:
        registry.load_from_package(Path(tmpdir))
