"""Tests for config differ."""

import pytest
from pydantic import BaseModel, Field

from unique_toolkit._common.config_checker.differ import (
    ConfigDiffer,
    DefaultChangeReport,
)


class SimpleConfig(BaseModel):
    name: str = "default_name"
    value: int = 42


class NestedConfig(BaseModel):
    simple: SimpleConfig = Field(default_factory=SimpleConfig)
    enabled: bool = True


class ListConfig(BaseModel):
    items: list[str] = Field(default_factory=lambda: ["a", "b"])
    tags: list[int] = Field(default_factory=list)


class DictConfig(BaseModel):
    metadata: dict[str, str] = Field(default_factory=lambda: {"version": "1.0"})


@pytest.mark.ai
def test_differ_detects_scalar_changes():
    """Test that differ detects scalar value changes."""
    differ = ConfigDiffer()

    old_json = {"name": "default_name", "value": 42}
    new_instance = SimpleConfig(name="default_name", value=100)

    changes = differ.compare_defaults(old_json, new_instance)

    assert len(changes) == 1
    assert changes[0].field_path == "value"
    assert changes[0].old_value == 42
    assert changes[0].new_value == 100


@pytest.mark.ai
def test_differ_detects_nested_changes():
    """Test that differ detects changes in nested models."""
    differ = ConfigDiffer()

    old_json = {"simple": {"name": "default_name", "value": 42}, "enabled": True}
    new_instance = NestedConfig(simple=SimpleConfig(value=99), enabled=True)

    changes = differ.compare_defaults(old_json, new_instance)

    assert len(changes) > 0
    # Should have found the nested value change
    value_changes = [c for c in changes if "value" in c.field_path]
    assert len(value_changes) > 0


@pytest.mark.ai
def test_differ_detects_list_changes():
    """Test that differ detects list value changes."""
    differ = ConfigDiffer()

    old_json = {"items": ["a", "b"], "tags": []}
    new_instance = ListConfig(items=["a", "b", "c"], tags=[])

    changes = differ.compare_defaults(old_json, new_instance)

    assert len(changes) > 0
    items_changes = [c for c in changes if "items" in c.field_path]
    assert len(items_changes) > 0
    assert items_changes[0].old_value == ["a", "b"]
    assert items_changes[0].new_value == ["a", "b", "c"]


@pytest.mark.ai
def test_differ_detects_dict_changes():
    """Test that differ detects dict value changes."""
    differ = ConfigDiffer()

    old_json = {"metadata": {"version": "1.0"}}
    new_instance = DictConfig(metadata={"version": "2.0"})

    changes = differ.compare_defaults(old_json, new_instance)

    assert len(changes) > 0
    metadata_changes = [c for c in changes if "metadata" in c.field_path]
    assert len(metadata_changes) > 0


@pytest.mark.ai
def test_differ_ignores_new_fields():
    """Test that differ doesn't report new fields as changes."""

    class OldConfig(BaseModel):
        name: str = "test"

    class NewConfig(BaseModel):
        name: str = "test"
        new_field: str = "new"

    differ = ConfigDiffer()

    old_json = {"name": "test"}
    new_instance = NewConfig(name="test", new_field="new")

    changes = differ.compare_defaults(old_json, new_instance)

    # New field shouldn't be reported as a change
    assert len([c for c in changes if "new_field" in c.field_path]) == 0


@pytest.mark.ai
def test_differ_ignores_removed_fields():
    """Test that differ doesn't report removed fields as changes."""

    class OldConfig(BaseModel):
        name: str = "test"
        removed_field: str = "old"

    class NewConfig(BaseModel):
        name: str = "test"

    differ = ConfigDiffer()

    old_json = {"name": "test", "removed_field": "old"}
    new_instance = NewConfig(name="test")

    changes = differ.compare_defaults(old_json, new_instance)

    # Removed field shouldn't be reported as a change by the differ
    # (that's a schema change, caught by validator)
    assert len([c for c in changes if "removed_field" in c.field_path]) == 0


@pytest.mark.ai
def test_differ_no_changes_on_identical_values():
    """Test that differ reports no changes when values are identical."""
    differ = ConfigDiffer()

    old_json = {"name": "default_name", "value": 42}
    new_instance = SimpleConfig()

    changes = differ.compare_defaults(old_json, new_instance)

    assert len(changes) == 0


@pytest.mark.ai
def test_differ_no_changes_on_reordered_lists():
    """Test that differ ignores order changes in lists (handles sets)."""
    differ = ConfigDiffer()

    old_json = {"items": ["a", "b", "c"]}
    new_instance = ListConfig(items=["c", "b", "a"])

    changes = differ.compare_defaults(old_json, new_instance)

    # Reordering shouldn't be reported as a change
    assert len(changes) == 0


@pytest.mark.ai
def test_differ_format_summary_no_changes():
    """Test DefaultChangeReport.format_summary with no changes."""
    report = DefaultChangeReport(config_name="Test", changes=[])
    assert report.format_summary() == ""


@pytest.mark.ai
def test_default_change_report_format():
    """Test DefaultChangeReport formatting."""
    from unique_toolkit._common.config_checker.models import DefaultChange

    changes = [
        DefaultChange(field_path="value", old_value=42, new_value=100),
        DefaultChange(field_path="name", old_value="old", new_value="new"),
    ]

    report = DefaultChangeReport(config_name="TestConfig", changes=changes)

    assert report.has_changes()
    assert "TestConfig" in report.format_summary()
    assert "value" in report.format_summary()
    assert "name" in report.format_summary()
