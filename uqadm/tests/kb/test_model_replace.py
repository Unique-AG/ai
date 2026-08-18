"""Tests for ``uqadm kb ingestion model-replace``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from uqadm.kb.model_replace import cmd_model_replace

OLD = "AZURE_GPT_4o_2024_0806"
NEW = "AZURE_GPT_5_2025_0807"


def _ingestion_config(model: str | dict[str, Any] = OLD) -> dict[str, Any]:
    return {
        "uniqueIngestionMode": "STANDARD",
        "chunkMaxTokens": 1000,
        "vttConfig": {"languageModel": model},
        "metadataExtractionConfig": {"enabled": True, "languageModel": model},
        "pdfConfig": {
            "imageContentExtraction": {"enabled": True, "languageModel": model}
        },
        "chunkingConfiguration": {
            "chunkStrategy": "CONTEXTUAL_CHUNKING",
            "model": model,
        },
    }


def _folder_info(
    scope_id: str = "scope_1", model: str | dict[str, Any] = OLD
) -> dict[str, Any]:
    return {
        "id": scope_id,
        "name": "HR",
        "ingestionConfig": _ingestion_config(model),
        "parentId": None,
    }


class _Cfg:
    user_id = "user_1"
    company_id = "company_1"


# --- mode validation ---


def _base_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "folder_path": None,
        "scope_id": None,
        "file_path": None,
        "sweep_all": False,
        "from_model": OLD,
        "to_model": NEW,
        "output": None,
        "apply_to_subfolders": False,
        "dry_run": False,
        "assume_yes": False,
    }
    kwargs.update(overrides)
    return kwargs


def test_requires_exactly_one_input_mode() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cmd_model_replace(None, **_base_kwargs())
    assert exc_info.value.code == 2


def test_folder_path_and_scope_id_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cmd_model_replace(
            None, **_base_kwargs(folder_path="/Dept/HR", scope_id="scope_1")
        )
    assert exc_info.value.code == 2


def test_output_rejected_with_all(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cmd_model_replace(
            _Cfg(), **_base_kwargs(sweep_all=True, output=tmp_path / "out.yaml")
        )
    assert exc_info.value.code == 2


# --- file mode ---


def test_file_mode_writes_rewritten_config(tmp_path: Path) -> None:
    config_file = tmp_path / "ingest.yaml"
    config_file.write_text(yaml.safe_dump(_ingestion_config()), encoding="utf-8")
    out = tmp_path / "ingest.migrated.yaml"
    cmd_model_replace(None, **_base_kwargs(file_path=config_file, output=out))
    rewritten = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert rewritten["vttConfig"]["languageModel"] == NEW
    assert rewritten["metadataExtractionConfig"]["languageModel"] == NEW
    assert rewritten["pdfConfig"]["imageContentExtraction"]["languageModel"] == NEW
    assert rewritten["chunkingConfiguration"]["model"] == NEW
    assert rewritten["chunkingConfiguration"]["chunkStrategy"] == (
        "CONTEXTUAL_CHUNKING"
    )
    assert rewritten["chunkMaxTokens"] == 1000


def test_file_mode_with_model_info_file_writes_object(tmp_path: Path) -> None:
    config_file = tmp_path / "ingest.json"
    config_file.write_text(json.dumps(_ingestion_config()), encoding="utf-8")
    model_file = tmp_path / "new-model.json"
    model_file.write_text(
        json.dumps({"name": NEW, "provider": "CUSTOM"}), encoding="utf-8"
    )
    out = tmp_path / "out.json"
    cmd_model_replace(
        None,
        **_base_kwargs(file_path=config_file, to_model=str(model_file), output=out),
    )
    rewritten = json.loads(out.read_text(encoding="utf-8"))
    assert rewritten["vttConfig"]["languageModel"] == {
        "name": NEW,
        "provider": "CUSTOM",
    }


def test_unresolvable_to_model_path_exits_2(tmp_path: Path) -> None:
    config_file = tmp_path / "ingest.json"
    config_file.write_text(json.dumps(_ingestion_config()), encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        cmd_model_replace(
            None,
            **_base_kwargs(
                file_path=config_file,
                to_model=str(tmp_path / "missing-model.yaml"),
            ),
        )
    assert exc_info.value.code == 2


def test_file_mode_stdout_when_no_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file = tmp_path / "ingest.json"
    config_file.write_text(json.dumps(_ingestion_config()), encoding="utf-8")
    cmd_model_replace(None, **_base_kwargs(file_path=config_file))
    printed = json.loads(capsys.readouterr().out)
    assert printed["vttConfig"]["languageModel"] == NEW


# --- live single-folder mode ---


def test_single_folder_updates_and_verifies() -> None:
    with patch("uqadm.kb.model_replace.Folder") as folder_mock:
        folder_mock.get_info.side_effect = [
            _folder_info(),  # initial read
            _folder_info(model=NEW),  # verification re-read
        ]
        folder_mock.get_folder_path.return_value = {"folderPath": "/Dept/HR"}
        cmd_model_replace(_Cfg(), **_base_kwargs(folder_path="/Dept/HR"))

    folder_mock.update_ingestion_config.assert_called_once()
    kwargs = folder_mock.update_ingestion_config.call_args.kwargs
    assert kwargs["scopeId"] == "scope_1"
    assert kwargs["applyToSubScopes"] is False
    assert kwargs["ingestionConfig"]["vttConfig"]["languageModel"] == NEW
    assert kwargs["ingestionConfig"]["chunkingConfiguration"]["model"] == NEW


def test_single_folder_subfolders_flag_sets_apply_to_sub_scopes() -> None:
    with patch("uqadm.kb.model_replace.Folder") as folder_mock:
        folder_mock.get_info.side_effect = [
            _folder_info(),
            _folder_info(model=NEW),
        ]
        folder_mock.get_folder_path.return_value = {"folderPath": "/Dept/HR"}
        cmd_model_replace(
            _Cfg(), **_base_kwargs(scope_id="scope_1", apply_to_subfolders=True)
        )
    kwargs = folder_mock.update_ingestion_config.call_args.kwargs
    assert kwargs["applyToSubScopes"] is True


def test_single_folder_accepts_model_info_keeping_the_old_name(tmp_path: Path) -> None:
    """`--to-model FILE` may carry the replaced name; only the shape changes."""
    info = {"name": OLD, "provider": "CUSTOM"}
    model_file = tmp_path / "model.json"
    model_file.write_text(json.dumps(info), encoding="utf-8")
    with patch("uqadm.kb.model_replace.Folder") as folder_mock:
        folder_mock.get_info.side_effect = [
            _folder_info(),
            _folder_info(model=info),
        ]
        folder_mock.get_folder_path.return_value = {"folderPath": "/Dept/HR"}
        cmd_model_replace(
            _Cfg(), **_base_kwargs(folder_path="/Dept/HR", to_model=str(model_file))
        )
    kwargs = folder_mock.update_ingestion_config.call_args.kwargs
    assert kwargs["ingestionConfig"]["vttConfig"]["languageModel"] == info


def test_single_folder_verification_failure_exits_1() -> None:
    with patch("uqadm.kb.model_replace.Folder") as folder_mock:
        reread = _folder_info(model=NEW)
        del reread["ingestionConfig"]["metadataExtractionConfig"]
        folder_mock.get_info.side_effect = [_folder_info(), reread]
        folder_mock.get_folder_path.return_value = {"folderPath": "/Dept/HR"}
        with pytest.raises(SystemExit) as exc_info:
            cmd_model_replace(_Cfg(), **_base_kwargs(folder_path="/Dept/HR"))
    assert exc_info.value.code == 1


def test_single_folder_dry_run_does_not_update() -> None:
    with patch("uqadm.kb.model_replace.Folder") as folder_mock:
        folder_mock.get_info.return_value = _folder_info()
        folder_mock.get_folder_path.return_value = {"folderPath": "/Dept/HR"}
        cmd_model_replace(_Cfg(), **_base_kwargs(folder_path="/Dept/HR", dry_run=True))
    folder_mock.update_ingestion_config.assert_not_called()


def test_single_folder_no_matches_does_not_update() -> None:
    with patch("uqadm.kb.model_replace.Folder") as folder_mock:
        folder_mock.get_info.return_value = _folder_info(model="OTHER_MODEL")
        folder_mock.get_folder_path.return_value = {"folderPath": "/Dept/HR"}
        cmd_model_replace(_Cfg(), **_base_kwargs(folder_path="/Dept/HR"))
    folder_mock.update_ingestion_config.assert_not_called()


def test_single_folder_dry_run_with_output_writes_nothing(tmp_path: Path) -> None:
    out = tmp_path / "config.json"
    with patch("uqadm.kb.model_replace.Folder") as folder_mock:
        folder_mock.get_info.return_value = _folder_info()
        folder_mock.get_folder_path.return_value = {"folderPath": "/Dept/HR"}
        cmd_model_replace(
            _Cfg(), **_base_kwargs(folder_path="/Dept/HR", output=out, dry_run=True)
        )
    folder_mock.update_ingestion_config.assert_not_called()
    assert not out.exists()


def test_single_folder_output_writes_file_without_update(tmp_path: Path) -> None:
    out = tmp_path / "config.json"
    with patch("uqadm.kb.model_replace.Folder") as folder_mock:
        folder_mock.get_info.return_value = _folder_info()
        folder_mock.get_folder_path.return_value = {"folderPath": "/Dept/HR"}
        cmd_model_replace(_Cfg(), **_base_kwargs(folder_path="/Dept/HR", output=out))
    folder_mock.update_ingestion_config.assert_not_called()
    rewritten = json.loads(out.read_text(encoding="utf-8"))
    assert rewritten["vttConfig"]["languageModel"] == NEW


# --- sweep (--all) mode ---


def _tree() -> dict[str | None, list[dict[str, Any]]]:
    """Root has two folders; scope_1 has a matching child; scope_2 is clean."""
    child = _folder_info("scope_child")
    child["parentId"] = "scope_1"
    clean = _folder_info("scope_2", model="OTHER_MODEL")
    return {
        None: [_folder_info("scope_1"), clean],
        "scope_1": [child],
        "scope_2": [],
        "scope_child": [],
    }


def _patch_folder_tree(
    folder_mock: Any, tree: dict[str | None, list[dict[str, Any]]]
) -> None:
    def get_infos(_user: str, _company: str, **params: Any) -> dict[str, Any]:
        infos = tree[params.get("parentId")]
        return {"folderInfos": infos, "totalCount": len(infos)}

    folder_mock.get_infos.side_effect = get_infos
    folder_mock.get_folder_path.side_effect = lambda _u, _c, sid: {
        "folderPath": f"/path/{sid}"
    }
    folder_mock.get_info.side_effect = lambda _u, _c, **params: _folder_info(
        params["scopeId"], model=NEW
    )


def test_sweep_walks_tree_and_prompts_per_match() -> None:
    with (
        patch("uqadm.kb.model_replace.Folder") as folder_mock,
        patch(
            "uqadm.kb.model_replace.confirm_each",
            side_effect=["yes", "yes"],
        ) as confirm_mock,
    ):
        _patch_folder_tree(folder_mock, _tree())
        cmd_model_replace(_Cfg(), **_base_kwargs(sweep_all=True))

    assert confirm_mock.call_count == 2  # scope_1 and scope_child; scope_2 clean
    assert folder_mock.update_ingestion_config.call_count == 2
    updated_scopes = {
        call.kwargs["scopeId"]
        for call in folder_mock.update_ingestion_config.call_args_list
    }
    assert updated_scopes == {"scope_1", "scope_child"}
    for call in folder_mock.update_ingestion_config.call_args_list:
        assert call.kwargs["applyToSubScopes"] is False


def test_sweep_quit_aborts() -> None:
    with (
        patch("uqadm.kb.model_replace.Folder") as folder_mock,
        patch("uqadm.kb.model_replace.confirm_each", side_effect=["quit"]),
    ):
        _patch_folder_tree(folder_mock, _tree())
        cmd_model_replace(_Cfg(), **_base_kwargs(sweep_all=True))
    folder_mock.update_ingestion_config.assert_not_called()


def test_sweep_dry_run_never_updates_or_prompts() -> None:
    with (
        patch("uqadm.kb.model_replace.Folder") as folder_mock,
        patch("uqadm.kb.model_replace.confirm_each") as confirm_mock,
    ):
        _patch_folder_tree(folder_mock, _tree())
        cmd_model_replace(_Cfg(), **_base_kwargs(sweep_all=True, dry_run=True))
    confirm_mock.assert_not_called()
    folder_mock.update_ingestion_config.assert_not_called()


def test_sweep_verification_failure_exits_1() -> None:
    tree = _tree()
    with (
        patch("uqadm.kb.model_replace.Folder") as folder_mock,
    ):
        _patch_folder_tree(folder_mock, tree)
        # Re-reads show the old model still in place: verification must fail.
        folder_mock.get_info.side_effect = lambda _u, _c, **params: _folder_info(
            params["scopeId"], model=OLD
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_model_replace(_Cfg(), **_base_kwargs(sweep_all=True, assume_yes=True))
    assert exc_info.value.code == 1
