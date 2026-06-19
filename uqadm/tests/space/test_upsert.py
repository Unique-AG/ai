"""Tests for ``uqadm space upsert`` command helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uqadm.core.payload_files import snapshot_format_for_path
from uqadm.space.migrate import assistant_prompt_params_from_source
from uqadm.space.upsert import cmd_upsert, load_space_snapshot


def _minimal_create_snapshot() -> dict[str, object]:
    return {
        "name": "NewSpace",
        "fallbackModule": "fallback_mod",
        "modules": [],
    }


# --- snapshot_format_for_path ---


def test_snapshot_format_rejects_bad_suffix() -> None:
    with pytest.raises(ValueError, match=r"must end with \.json, \.yaml, or \.yml"):
        snapshot_format_for_path(Path("snap.txt"))


def test_snapshot_format_json_case_insensitive() -> None:
    assert snapshot_format_for_path(Path("x.JSON")) == "json"


# --- load_space_snapshot ---


def test_load_space_snapshot_json_roundtrip(tmp_path: Path) -> None:
    data = {"name": "S", "fallbackModule": "fm", "modules": [{"name": "m"}]}
    path = tmp_path / "s.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_space_snapshot(path) == data


def test_load_space_snapshot_yaml_roundtrip(tmp_path: Path) -> None:
    import yaml

    data = {"name": "S", "fallbackModule": "fm"}
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert load_space_snapshot(path) == data


def test_load_space_snapshot_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match=r"mapping"):
        load_space_snapshot(path)


# --- cmd_upsert ---


def test_upsert_bad_snapshot_suffix_exits_2(tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        cmd_upsert(bad, "qa", target_space_id=None, dry_run=False, cwd=None)
    assert exc_info.value.code == 2


def test_upsert_create_requires_fallback_module(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"name": "OnlyName"}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        cmd_upsert(path, "qa", target_space_id=None, dry_run=True, cwd=None)
    assert exc_info.value.code == 2


@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_create_dry_run_no_writes(
    mock_cfg: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u", company_id="c")
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(_minimal_create_snapshot()), encoding="utf-8")
    with patch("uqadm.space.upsert.Space.create_space") as mock_create:
        cmd_upsert(path, "qa", target_space_id=None, dry_run=True, cwd=None)
        mock_create.assert_not_called()
    out = capsys.readouterr().out
    assert "Dry-run: would create_space" in out


@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_update_dry_run_no_writes(
    mock_cfg: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u", company_id="c")
    path = tmp_path / "snap.json"
    path.write_text(
        json.dumps(
            {
                "name": "Updated",
                "modules": [{"name": "alpha", "configuration": {"k": 1}}],
            }
        ),
        encoding="utf-8",
    )
    dest_modules = [{"id": "mod_1", "name": "alpha"}]
    with patch(
        "uqadm.space.upsert.Space.get_space",
        return_value={"modules": dest_modules},
    ) as mock_get:
        with patch("uqadm.space.upsert.Space.update_space") as mock_up:
            cmd_upsert(path, "qa", target_space_id="space_dst", dry_run=True, cwd=None)
            mock_up.assert_not_called()
        mock_get.assert_called_once_with("u", "c", "space_dst")
    out = capsys.readouterr().out
    assert "Dry-run: would update_space" in out


def test_assistant_prompt_params_from_source_strips_export_fields() -> None:
    prompts = assistant_prompt_params_from_source(
        [
            {
                "id": "prompt_1",
                "object": "assistant-prompt",
                "order": 0,
                "title": "Summarize",
                "prompt": "Please summarize",
            }
        ]
    )
    assert prompts == [
        {
            "id": "prompt_1",
            "order": 0,
            "title": "Summarize",
            "prompt": "Please summarize",
        }
    ]


def test_build_update_kwargs_includes_empty_assistant_prompts() -> None:
    from uqadm.space.migrate import build_update_kwargs

    kwargs = build_update_kwargs({"name": "S", "assistantPrompts": []})
    assert kwargs["assistantPrompts"] == []
    assert kwargs["name"] == "S"


def test_build_create_params_maps_assistant_prompts() -> None:
    from uqadm.space.migrate import build_create_params

    params = build_create_params(
        {
            "name": "S",
            "fallbackModule": "fm",
            "modules": [],
            "assistantPrompts": [
                {"title": "T", "prompt": "P", "order": 1},
            ],
        }
    )
    assert params["assistantPrompts"] == [
        {"title": "T", "prompt": "P", "order": 1},
    ]
