"""Tests for ``uqadm space model-replace``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from uqadm.space.model_replace import build_model_update_kwargs, cmd_model_replace

OLD = "AZURE_GPT_4o_2024_0806"
NEW = "AZURE_GPT_5_2025_0807"


def _space(space_id: str = "asst_1") -> dict[str, Any]:
    return {
        "id": space_id,
        "name": "My Space",
        "languageModel": OLD,
        "settings": {"foo": "bar"},
        "switchableLanguageModels": [
            {"displayName": "GPT-4o", "languageModel": OLD},
        ],
        "modules": [
            {
                "id": "mod_1",
                "name": "UniqueAI",
                "configuration": {"languageModel": OLD},
            },
            {
                "id": "mod_2",
                "name": "Untouched",
                "configuration": {"languageModel": "OTHER_MODEL"},
            },
        ],
    }


def _cfg() -> MagicMock:
    cfg = MagicMock()
    cfg.user_id = "user_1"
    cfg.company_id = "company_1"
    return cfg


class _SpaceApi:
    """Stand-in for ``Space`` that stores what ``update_space`` writes.

    The command re-reads every space it updates, so the double has to answer
    the second read with the result of the write rather than the original
    payload. ``apply_updates=False`` models an API that accepts a write and
    keeps none of it.
    """

    def __init__(
        self, spaces: list[dict[str, Any]], *, apply_updates: bool = True
    ) -> None:
        self._spaces = {space["id"]: space for space in spaces}
        self._apply_updates = apply_updates
        self.get_space = MagicMock(side_effect=self._get_space)
        self.update_space = MagicMock(side_effect=self._update_space)

    def _get_space(self, _user: str, _company: str, space_id: str) -> dict[str, Any]:
        return json.loads(json.dumps(self._spaces[space_id]))

    def _update_space(
        self, _user: str, _company: str, space_id: str, **kwargs: Any
    ) -> None:
        if not self._apply_updates:
            return
        space = self._spaces[space_id]
        for key, value in kwargs.items():
            if key != "modules":
                space[key] = value
                continue
            by_id = {update["moduleId"]: update for update in value}
            for module in space["modules"]:
                update = by_id.get(module["id"])
                if update is not None:
                    module["configuration"] = update["configuration"]


# --- build_model_update_kwargs ---


def test_build_model_update_kwargs_sends_only_changed_fields() -> None:
    old = _space()
    new = json.loads(json.dumps(old))
    new["languageModel"] = NEW
    new["switchableLanguageModels"][0]["languageModel"] = NEW
    new["modules"][0]["configuration"]["languageModel"] = NEW

    kwargs, unsupported = build_model_update_kwargs(old, new)
    assert unsupported == []
    assert kwargs == {
        "languageModel": NEW,
        "switchableLanguageModels": [{"displayName": "GPT-4o", "languageModel": NEW}],
        "modules": [{"moduleId": "mod_1", "configuration": {"languageModel": NEW}}],
    }


def test_build_model_update_kwargs_reports_unsupported_fields() -> None:
    old = {"scopeRules": [{"model": OLD}], "modules": []}
    new = {"scopeRules": [{"model": NEW}], "modules": []}
    kwargs, unsupported = build_model_update_kwargs(old, new)
    assert kwargs == {}
    assert unsupported == ["scopeRules"]


def test_build_model_update_kwargs_reports_module_field_outside_configuration() -> None:
    """update_space writes modules through `configuration` and nothing else."""
    old = {
        "modules": [
            {"id": "mod_1", "toolDefinition": {"model": OLD}, "configuration": {}}
        ]
    }
    new = {
        "modules": [
            {"id": "mod_1", "toolDefinition": {"model": NEW}, "configuration": {}}
        ]
    }
    kwargs, unsupported = build_model_update_kwargs(old, new)
    assert kwargs == {}
    assert unsupported == ["modules[0].toolDefinition"]


def test_build_model_update_kwargs_reports_module_without_id() -> None:
    old = {"modules": [{"name": "m", "configuration": {"model": OLD}}]}
    new = {"modules": [{"name": "m", "configuration": {"model": NEW}}]}
    kwargs, unsupported = build_model_update_kwargs(old, new)
    assert kwargs == {}
    assert unsupported == ["modules[0] (missing module id)"]


def test_build_model_update_kwargs_no_changes() -> None:
    old = _space()
    kwargs, unsupported = build_model_update_kwargs(old, json.loads(json.dumps(old)))
    assert kwargs == {}
    assert unsupported == []


# --- mode validation ---


def test_requires_exactly_one_input_mode() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cmd_model_replace(
            None,
            space_id=None,
            file_path=None,
            sweep_all=False,
            name_filter=None,
            from_model=OLD,
            to_model=NEW,
            output=None,
            dry_run=False,
            assume_yes=False,
        )
    assert exc_info.value.code == 2


def test_output_rejected_with_all(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cmd_model_replace(
            _cfg(),
            space_id=None,
            file_path=None,
            sweep_all=True,
            name_filter=None,
            from_model=OLD,
            to_model=NEW,
            output=tmp_path / "out.yaml",
            dry_run=False,
            assume_yes=False,
        )
    assert exc_info.value.code == 2


def test_unresolvable_to_model_path_exits_2(tmp_path: Path) -> None:
    snapshot = tmp_path / "s.json"
    snapshot.write_text(json.dumps(_space()), encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        cmd_model_replace(
            None,
            space_id=None,
            file_path=snapshot,
            sweep_all=False,
            name_filter=None,
            from_model=OLD,
            to_model=str(tmp_path / "missing-model.yaml"),
            output=None,
            dry_run=False,
            assume_yes=False,
        )
    assert exc_info.value.code == 2


# --- file mode ---


def _run_file(file_path: Path, output: Path | None, *, dry_run: bool = False) -> None:
    cmd_model_replace(
        None,
        space_id=None,
        file_path=file_path,
        sweep_all=False,
        name_filter=None,
        from_model=OLD,
        to_model=NEW,
        output=output,
        dry_run=dry_run,
        assume_yes=False,
    )


def test_file_mode_writes_rewritten_yaml(tmp_path: Path) -> None:
    snapshot = tmp_path / "s.json"
    snapshot.write_text(json.dumps(_space()), encoding="utf-8")
    out = tmp_path / "out.yaml"
    _run_file(snapshot, out)
    rewritten = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert rewritten["languageModel"] == NEW
    assert rewritten["switchableLanguageModels"][0]["languageModel"] == NEW
    assert rewritten["modules"][0]["configuration"]["languageModel"] == NEW
    assert rewritten["modules"][1]["configuration"]["languageModel"] == "OTHER_MODEL"


def test_file_mode_stdout_when_no_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot = tmp_path / "s.json"
    snapshot.write_text(json.dumps(_space()), encoding="utf-8")
    _run_file(snapshot, None)
    printed = json.loads(capsys.readouterr().out)
    assert printed["languageModel"] == NEW


def test_file_mode_with_model_info_file_writes_object(tmp_path: Path) -> None:
    snapshot = tmp_path / "s.json"
    snapshot.write_text(json.dumps(_space()), encoding="utf-8")
    model_file = tmp_path / "new-model.yaml"
    model_file.write_text(f"name: {NEW}\nprovider: CUSTOM\n", encoding="utf-8")
    out = tmp_path / "out.json"
    cmd_model_replace(
        None,
        space_id=None,
        file_path=snapshot,
        sweep_all=False,
        name_filter=None,
        from_model=OLD,
        to_model=str(model_file),
        output=out,
        dry_run=False,
        assume_yes=False,
    )
    rewritten = json.loads(out.read_text(encoding="utf-8"))
    expected = {"name": NEW, "provider": "CUSTOM"}
    assert rewritten["languageModel"] == expected
    assert rewritten["modules"][0]["configuration"]["languageModel"] == expected


def test_file_mode_dry_run_writes_nothing(tmp_path: Path) -> None:
    snapshot = tmp_path / "s.json"
    snapshot.write_text(json.dumps(_space()), encoding="utf-8")
    out = tmp_path / "out.yaml"
    _run_file(snapshot, out, dry_run=True)
    assert not out.exists()


# --- live single-space mode ---


def _run_single(
    space_id: str = "asst_1",
    *,
    output: Path | None = None,
    dry_run: bool = False,
) -> None:
    cmd_model_replace(
        _cfg(),
        space_id=space_id,
        file_path=None,
        sweep_all=False,
        name_filter=None,
        from_model=OLD,
        to_model=NEW,
        output=output,
        dry_run=dry_run,
        assume_yes=False,
    )


def test_single_space_sends_minimal_update() -> None:
    api = _SpaceApi([_space()])
    with patch("uqadm.space.model_replace.Space", api):
        _run_single()
    api.update_space.assert_called_once()
    kwargs = api.update_space.call_args.kwargs
    assert kwargs["languageModel"] == NEW
    assert kwargs["modules"] == [
        {"moduleId": "mod_1", "configuration": {"languageModel": NEW}}
    ]
    assert "settings" not in kwargs
    assert "name" not in kwargs


def test_single_space_verifies_the_update_by_re_reading() -> None:
    api = _SpaceApi([_space()])
    with patch("uqadm.space.model_replace.Space", api):
        _run_single()
    assert api.get_space.call_count == 2


def test_single_space_ignored_write_fails_verification() -> None:
    api = _SpaceApi([_space()], apply_updates=False)
    with patch("uqadm.space.model_replace.Space", api):
        with pytest.raises(SystemExit) as exc_info:
            _run_single()
    assert exc_info.value.code == 1


def test_single_space_partially_ignored_write_fails_verification(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A module the API silently left alone must not report as updated."""
    api = _SpaceApi([_space()])
    original_update = api.update_space.side_effect

    def drop_modules(*args: Any, **kwargs: Any) -> None:
        kwargs.pop("modules", None)
        original_update(*args, **kwargs)

    api.update_space.side_effect = drop_modules
    with patch("uqadm.space.model_replace.Space", api):
        with pytest.raises(SystemExit) as exc_info:
            _run_single()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert f"modules[0].configuration.languageModel: still set to {OLD!r}" in err


def test_single_space_dry_run_does_not_update() -> None:
    api = _SpaceApi([_space()])
    with patch("uqadm.space.model_replace.Space", api):
        _run_single(dry_run=True)
    api.update_space.assert_not_called()


def test_single_space_dry_run_with_output_writes_nothing(tmp_path: Path) -> None:
    out = tmp_path / "snapshot.json"
    api = _SpaceApi([_space()])
    with patch("uqadm.space.model_replace.Space", api):
        _run_single(output=out, dry_run=True)
    api.update_space.assert_not_called()
    assert not out.exists()


def test_single_space_no_matches_does_not_update() -> None:
    payload = _space()
    payload["languageModel"] = "OTHER_MODEL"
    payload["switchableLanguageModels"][0]["languageModel"] = "OTHER_MODEL"
    payload["modules"][0]["configuration"]["languageModel"] = "OTHER_MODEL"
    api = _SpaceApi([payload])
    with patch("uqadm.space.model_replace.Space", api):
        _run_single()
    api.update_space.assert_not_called()


def test_single_space_output_writes_file_without_update(tmp_path: Path) -> None:
    out = tmp_path / "snapshot.json"
    api = _SpaceApi([_space()])
    with patch("uqadm.space.model_replace.Space", api):
        _run_single(output=out)
    api.update_space.assert_not_called()
    rewritten = json.loads(out.read_text(encoding="utf-8"))
    assert rewritten["languageModel"] == NEW


def test_single_space_refuses_update_with_unwritable_match(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A match update_space cannot carry must fail, not warn and half-apply."""
    payload = _space()
    payload["modules"][0]["toolDefinition"] = {"languageModel": OLD}
    api = _SpaceApi([payload])
    with patch("uqadm.space.model_replace.Space", api):
        with pytest.raises(SystemExit) as exc_info:
            _run_single()
    assert exc_info.value.code == 1
    api.update_space.assert_not_called()
    assert "modules[0].toolDefinition" in capsys.readouterr().err


def test_single_space_update_failure_exits_1() -> None:
    api = _SpaceApi([_space()])
    api.update_space.side_effect = RuntimeError("boom")
    with patch("uqadm.space.model_replace.Space", api):
        with pytest.raises(SystemExit) as exc_info:
            _run_single()
    assert exc_info.value.code == 1


# --- sweep (--all) mode ---


def _run_sweep(*, dry_run: bool = False, assume_yes: bool = False) -> None:
    cmd_model_replace(
        _cfg(),
        space_id=None,
        file_path=None,
        sweep_all=True,
        name_filter=None,
        from_model=OLD,
        to_model=NEW,
        output=None,
        dry_run=dry_run,
        assume_yes=assume_yes,
    )


def _sweep_spaces() -> list[dict[str, Any]]:
    matching_a = _space("asst_a")
    matching_b = _space("asst_b")
    non_matching = _space("asst_c")
    non_matching["languageModel"] = "OTHER_MODEL"
    non_matching["switchableLanguageModels"] = []
    non_matching["modules"] = []
    return [matching_a, matching_b, non_matching]


def _sweep_api(spaces: list[dict[str, Any]] | None = None, **kwargs: Any) -> _SpaceApi:
    return _SpaceApi(spaces if spaces is not None else _sweep_spaces(), **kwargs)


def _patch_sweep(api: _SpaceApi, ids: list[str]) -> Any:
    return (
        patch("uqadm.space.model_replace.Space", api),
        patch(
            "uqadm.space.model_replace.fetch_all_spaces",
            return_value=[{"id": space_id} for space_id in ids],
        ),
    )


_SWEEP_IDS = ["asst_a", "asst_b", "asst_c"]


def test_sweep_prompts_and_respects_no() -> None:
    api = _sweep_api()
    space_patch, list_patch = _patch_sweep(api, _SWEEP_IDS)
    with (
        space_patch,
        list_patch,
        patch(
            "uqadm.space.model_replace.confirm_each",
            side_effect=["yes", "no"],
        ) as confirm_mock,
    ):
        _run_sweep()
    assert confirm_mock.call_count == 2  # non-matching space never prompts
    api.update_space.assert_called_once()
    assert api.update_space.call_args.args[2] == "asst_a"


def test_sweep_all_answer_stops_prompting() -> None:
    api = _sweep_api()
    space_patch, list_patch = _patch_sweep(api, _SWEEP_IDS)
    with (
        space_patch,
        list_patch,
        patch(
            "uqadm.space.model_replace.confirm_each",
            side_effect=["all"],
        ) as confirm_mock,
    ):
        _run_sweep()
    assert confirm_mock.call_count == 1
    assert api.update_space.call_count == 2


def test_sweep_quit_aborts() -> None:
    api = _sweep_api()
    space_patch, list_patch = _patch_sweep(api, _SWEEP_IDS)
    with (
        space_patch,
        list_patch,
        patch("uqadm.space.model_replace.confirm_each", side_effect=["quit"]),
    ):
        _run_sweep()
    api.update_space.assert_not_called()


def test_sweep_yes_flag_skips_prompts() -> None:
    api = _sweep_api()
    space_patch, list_patch = _patch_sweep(api, _SWEEP_IDS)
    with (
        space_patch,
        list_patch,
        patch("uqadm.space.model_replace.confirm_each") as confirm_mock,
    ):
        _run_sweep(assume_yes=True)
    confirm_mock.assert_not_called()
    assert api.update_space.call_count == 2


def test_sweep_ignored_write_counts_as_failed() -> None:
    api = _sweep_api(apply_updates=False)
    space_patch, list_patch = _patch_sweep(api, _SWEEP_IDS)
    with space_patch, list_patch, pytest.raises(SystemExit) as exc_info:
        _run_sweep(assume_yes=True)
    assert exc_info.value.code == 1


def test_sweep_unwritable_match_fails_without_updating() -> None:
    spaces = _sweep_spaces()
    spaces[0]["modules"][0]["toolDefinition"] = {"languageModel": OLD}
    api = _sweep_api(spaces)
    space_patch, list_patch = _patch_sweep(api, _SWEEP_IDS)
    with space_patch, list_patch, pytest.raises(SystemExit) as exc_info:
        _run_sweep(assume_yes=True)
    assert exc_info.value.code == 1
    assert api.update_space.call_count == 1  # only the untouched second space
    assert api.update_space.call_args.args[2] == "asst_b"


def test_sweep_dry_run_never_updates_or_prompts() -> None:
    api = _sweep_api()
    space_patch, list_patch = _patch_sweep(api, _SWEEP_IDS)
    with (
        space_patch,
        list_patch,
        patch("uqadm.space.model_replace.confirm_each") as confirm_mock,
    ):
        _run_sweep(dry_run=True)
    confirm_mock.assert_not_called()
    api.update_space.assert_not_called()
