"""Tests for ``uqadm.core.payload_files``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from uqadm.core.payload_files import (
    load_json_or_yaml_mapping,
    read_path_list_file,
    snapshot_format_for_path,
)


def test_snapshot_format_rejects_bad_suffix() -> None:
    with pytest.raises(ValueError, match=r"\.json"):
        snapshot_format_for_path(Path("doc.txt"))


def test_load_json_mapping(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert load_json_or_yaml_mapping(p) == {"a": 1}


def test_load_yaml_mapping(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump({"x": "y"}), encoding="utf-8")
    assert load_json_or_yaml_mapping(p) == {"x": "y"}


def test_load_mapping_rejects_array_root(tmp_path: Path) -> None:
    p = tmp_path / "a.json"
    p.write_text("[1]", encoding="utf-8")
    with pytest.raises(ValueError, match=r"mapping"):
        load_json_or_yaml_mapping(p)


def test_read_path_list_file_strips_comments(tmp_path: Path) -> None:
    p = tmp_path / "paths.txt"
    p.write_text(
        " /a/b \n\n# skip\n/c/d # tail comment\n",
        encoding="utf-8",
    )
    assert read_path_list_file(p) == ["/a/b", "/c/d"]


def test_read_path_list_file_empty_ok(tmp_path: Path) -> None:
    p = tmp_path / "empty.txt"
    p.write_text("# only comment\n", encoding="utf-8")
    assert read_path_list_file(p) == []
