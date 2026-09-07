"""Tests for replacement-model resolution (``--to-model``)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uqadm.core.model_target import ModelTargetError, resolve_model_target

NEW = "AZURE_GPT_5_2025_0807"


def _write_info(
    tmp_path: Path, info: dict[str, object], name: str = "model.json"
) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(info), encoding="utf-8")
    return path


# --- bare model names ---


def test_plain_name_resolves_to_string() -> None:
    target = resolve_model_target(NEW)
    assert target.name == NEW
    assert target.value == NEW


def test_name_with_colon_prefix_is_not_treated_as_path() -> None:
    target = resolve_model_target("litellm:anthropic-claude-opus-4-6")
    assert target.value == "litellm:anthropic-claude-opus-4-6"


def test_empty_value_rejected() -> None:
    with pytest.raises(ModelTargetError, match="non-empty"):
        resolve_model_target("  ")


# --- file input ---


def test_existing_file_is_used_whole(tmp_path: Path) -> None:
    info = {"name": NEW, "provider": "AZURE", "version": "2025-08-07"}
    target = resolve_model_target(str(_write_info(tmp_path, info)))
    assert target.name == NEW
    assert target.value == info


def test_yaml_file_supported(tmp_path: Path) -> None:
    path = tmp_path / "model.yaml"
    path.write_text(f"name: {NEW}\nprovider: CUSTOM\n", encoding="utf-8")
    target = resolve_model_target(str(path))
    assert target.value == {"name": NEW, "provider": "CUSTOM"}


def test_file_without_name_rejected(tmp_path: Path) -> None:
    path = _write_info(tmp_path, {"provider": "AZURE"})
    with pytest.raises(ModelTargetError, match="non-empty string 'name'"):
        resolve_model_target(str(path))


def test_file_with_non_mapping_root_rejected(tmp_path: Path) -> None:
    path = tmp_path / "model.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ModelTargetError, match="mapping"):
        resolve_model_target(str(path))


def test_invalid_json_rejected(tmp_path: Path) -> None:
    path = tmp_path / "model.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ModelTargetError, match="Invalid JSON"):
        resolve_model_target(str(path))


# --- path-shaped values that do not resolve ---


def test_missing_file_with_config_suffix_rejected(tmp_path: Path) -> None:
    with pytest.raises(ModelTargetError, match="looks like a file path"):
        resolve_model_target(str(tmp_path / "does-not-exist.yaml"))


def test_missing_file_with_separator_rejected() -> None:
    with pytest.raises(ModelTargetError, match="looks like a file path"):
        resolve_model_target("./configs/new-model")


def test_typo_in_suffix_is_not_silently_a_model_name(tmp_path: Path) -> None:
    _write_info(tmp_path, {"name": NEW}, name="model.json")
    with pytest.raises(ModelTargetError, match="looks like a file path"):
        resolve_model_target(str(tmp_path / "modle.json"))
