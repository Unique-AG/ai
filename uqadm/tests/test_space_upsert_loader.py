"""Tests for snapshot loading used by ``space upsert``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from uqadm.space_upsert import load_space_snapshot, snapshot_format_for_path


def test_snapshot_format_rejects_bad_suffix() -> None:
    with pytest.raises(ValueError, match=r"must end with \.json, \.yaml, or \.yml"):
        snapshot_format_for_path(Path("snap.txt"))


def test_snapshot_format_json_case_insensitive() -> None:
    assert snapshot_format_for_path(Path("x.JSON")) == "json"


def test_load_space_snapshot_json_roundtrip(tmp_path: Path) -> None:
    data = {"name": "S", "fallbackModule": "fm", "modules": [{"name": "m"}]}
    path = tmp_path / "s.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_space_snapshot(path) == data


def test_load_space_snapshot_yaml_roundtrip(tmp_path: Path) -> None:
    data = {"name": "S", "fallbackModule": "fm"}
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert load_space_snapshot(path) == data


def test_load_space_snapshot_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match=r"mapping"):
        load_space_snapshot(path)
