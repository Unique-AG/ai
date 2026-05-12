"""Tests for space export YAML and output path suffix rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from uqadm.space_export import export_format_for_output_path
from uqadm.space_export_yaml import dump_space_snapshot_yaml


def test_export_format_json_suffix_case_insensitive() -> None:
    assert export_format_for_output_path(Path("backup.JSON")) == "json"


def test_export_format_yaml_suffixes() -> None:
    assert export_format_for_output_path(Path("dir/space.yaml")) == "yaml"
    assert export_format_for_output_path(Path("x.YML")) == "yaml"


def test_export_format_rejects_missing_or_wrong_suffix() -> None:
    with pytest.raises(ValueError, match=r"must end with \.json, \.yaml, or \.yml"):
        export_format_for_output_path(Path("backup"))
    with pytest.raises(ValueError, match=r"'out\.txt'"):
        export_format_for_output_path(Path("out.txt"))
    with pytest.raises(ValueError, match=r"\.jsonl"):
        export_format_for_output_path(Path("data.jsonl"))


def test_dump_space_snapshot_yaml_multiline_uses_block_style() -> None:
    normalized = {"prompt": "line1\nline2\nUse {{format}}", "id": "x"}
    text = dump_space_snapshot_yaml(normalized)
    assert "|" in text
    assert "line1" in text
    assert "{{format}}" in text


def test_dump_space_snapshot_yaml_roundtrip_matches_normalized() -> None:
    normalized = {
        "nested": {"a": 1},
        "prompt": "hello\nworld",
        "flag": True,
    }
    yaml_text = dump_space_snapshot_yaml(normalized)
    loaded = yaml.safe_load(yaml_text)
    assert loaded == normalized
