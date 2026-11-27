"""Tests for space export YAML and output path suffix rules."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from uqadm.space.export import cmd_export, export_format_for_output_path
from uqadm.space.export_yaml import dump_space_snapshot_yaml


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


@patch("uqadm.space.export.Space.get_space")
def test_cmd_export_stdout_walks_unique_object_as_mapping(
    mock_get: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class UniqueObject(dict):
        pass

    mock_get.return_value = UniqueObject(
        {
            "name": "S",
            "switchableLanguageModels": [
                UniqueObject(
                    {
                        "displayName": "GPT-4o",
                        "languageModel": UniqueObject(
                            {"name": "AZURE_GPT_4o_2024_0806"}
                        ),
                    }
                )
            ],
        }
    )
    cmd_export("space_x", cfg=MagicMock(user_id="u", company_id="c"), output=None)
    payload = json.loads(capsys.readouterr().out)
    assert payload["switchableLanguageModels"] == [
        {
            "displayName": "GPT-4o",
            "languageModel": {"name": "AZURE_GPT_4o_2024_0806"},
        }
    ]


@patch("uqadm.space.export.Space.get_space", return_value=["not-a-space"])
def test_cmd_export_rejects_non_mapping_payload(
    _mock_get: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cmd_export("space_x", cfg=MagicMock(user_id="u", company_id="c"), output=None)
    assert exc_info.value.code == 1
    assert "not a mapping" in capsys.readouterr().err
