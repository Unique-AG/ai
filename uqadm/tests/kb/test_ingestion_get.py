"""Tests for ``uqadm kb ingestion get``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from uqadm.kb.ingestion import cmd_ingestion_get


def _cfg() -> MagicMock:
    return MagicMock(user_id="u1", company_id="c1")


def _ingestion_config() -> dict[str, Any]:
    return {
        "uniqueIngestionMode": "STANDARD",
        "chunkMaxTokens": 1000,
        "vttConfig": {"languageModel": "AZURE_GPT_4o_2024_0806"},
    }


def _folder_info() -> dict[str, Any]:
    return {"id": "scope_1", "name": "HR", "ingestionConfig": _ingestion_config()}


def test_requires_folder_xor_scope() -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_get(_cfg(), folder_path="/a", scope_id="s", output=None)
    assert ei.value.code == 2


def test_requires_at_least_one_selector() -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_get(_cfg(), folder_path=None, scope_id=None, output=None)
    assert ei.value.code == 2


@patch("uqadm.kb.ingestion.Folder.get_info", return_value=_folder_info())
def test_folder_path_prints_config_as_json(
    mock_get: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    cmd_ingestion_get(_cfg(), folder_path="/Dept/HR", scope_id=None, output=None)
    mock_get.assert_called_once_with("u1", "c1", folderPath="/Dept/HR")
    assert json.loads(capsys.readouterr().out) == _ingestion_config()


@patch("uqadm.kb.ingestion.Folder.get_info", return_value=_folder_info())
def test_scope_id_selector(mock_get: MagicMock) -> None:
    cmd_ingestion_get(_cfg(), folder_path=None, scope_id="scope_1", output=None)
    mock_get.assert_called_once_with("u1", "c1", scopeId="scope_1")


@patch("uqadm.kb.ingestion.Folder.get_info", return_value=_folder_info())
def test_writes_yaml_file_and_keeps_stdout_clean(
    mock_get: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "nested" / "ingest.yaml"
    cmd_ingestion_get(_cfg(), folder_path="/Dept/HR", scope_id=None, output=out)
    assert yaml.safe_load(out.read_text(encoding="utf-8")) == _ingestion_config()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(out) in captured.err


@patch("uqadm.kb.ingestion.Folder.get_info", return_value=_folder_info())
def test_rejects_unsupported_output_suffix(mock_get: MagicMock, tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_get(
            _cfg(),
            folder_path="/Dept/HR",
            scope_id=None,
            output=tmp_path / "ingest.txt",
        )
    assert ei.value.code == 2


@patch("uqadm.kb.ingestion.Folder.get_info", return_value={"id": "scope_1"})
def test_missing_config_emits_empty_mapping(
    mock_get: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    cmd_ingestion_get(_cfg(), folder_path="/Empty", scope_id=None, output=None)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {}
    assert "no ingestion config" in captured.err


@patch("uqadm.kb.ingestion.Folder.get_info", side_effect=RuntimeError("not found"))
def test_api_failure_exits_1(
    mock_get: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as ei:
        cmd_ingestion_get(_cfg(), folder_path="/Dept/HR", scope_id=None, output=None)
    assert ei.value.code == 1
    assert "get_info failed" in capsys.readouterr().err
