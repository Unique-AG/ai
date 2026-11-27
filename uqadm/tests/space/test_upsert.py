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


def test_assistant_prompt_params_from_source_strips_export_only_fields() -> None:
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
    # The source `id` and `object` must be dropped so prompts are not bound to
    # the source space's identity; only content + order are forwarded.
    assert prompts == [
        {
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


def test_build_create_params_maps_model_switching() -> None:
    from uqadm.space.migrate import build_create_params

    params = build_create_params(
        {
            "name": "S",
            "fallbackModule": "fm",
            "modules": [],
            "allowModelSwitching": True,
            "switchableLanguageModels": [
                {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
            ],
        }
    )
    assert params["allowModelSwitching"] is True
    assert params["switchableLanguageModels"] == [
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
    ]


def test_switchable_language_model_params_strips_export_only_fields() -> None:
    from uqadm.space.migrate import switchable_language_model_params_from_source

    models = switchable_language_model_params_from_source(
        [
            {
                "id": "ignored",
                "object": "switchable-language-model",
                "displayName": "GPT-4o",
                "languageModel": "AZURE_GPT_4o_2024_0806",
                "temperature": 0.3,
            }
        ]
    )
    assert models == [
        {
            "displayName": "GPT-4o",
            "languageModel": "AZURE_GPT_4o_2024_0806",
            "temperature": 0.3,
        }
    ]


def test_switchable_language_model_params_unwraps_data_envelope() -> None:
    from uqadm.space.migrate import switchable_language_model_params_from_source

    models = switchable_language_model_params_from_source(
        {
            "object": "list",
            "data": [
                {
                    "displayName": "GPT-4o",
                    "languageModel": "AZURE_GPT_4o_2024_0806",
                }
            ],
        }
    )
    assert models == [
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
    ]


def test_switchable_language_model_params_accepts_single_mapping() -> None:
    from uqadm.space.migrate import switchable_language_model_params_from_source

    models = switchable_language_model_params_from_source(
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"}
    )
    assert models == [
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
    ]


def test_switchable_language_model_params_skips_non_model_mapping() -> None:
    from uqadm.space.migrate import switchable_language_model_params_from_source

    assert switchable_language_model_params_from_source({"object": "list"}) == []


def test_switchable_language_model_params_skips_non_dict_entries() -> None:
    from uqadm.space.migrate import switchable_language_model_params_from_source

    models = switchable_language_model_params_from_source(
        [
            "skip-me",
            {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
        ]
    )
    assert models == [
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
    ]


def test_switchable_language_model_params_skips_incomplete_entries() -> None:
    from uqadm.space.migrate import switchable_language_model_params_from_source

    models = switchable_language_model_params_from_source(
        [
            {"displayName": "NoModel"},
            {"languageModel": "AZURE_GPT_4o_2024_0806"},
            {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
        ]
    )
    assert models == [
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
    ]


def test_switchable_language_model_params_accepts_dict_subclass_entries() -> None:
    from uqadm.space.migrate import switchable_language_model_params_from_source

    class UniqueObject(dict):
        pass

    models = switchable_language_model_params_from_source(
        [
            UniqueObject(
                {
                    "object": "x",
                    "displayName": "GPT-4o",
                    "languageModel": UniqueObject({"name": "AZURE_GPT_4o_2024_0806"}),
                }
            )
        ]
    )
    assert models == [
        {
            "displayName": "GPT-4o",
            "languageModel": {"name": "AZURE_GPT_4o_2024_0806"},
        }
    ]


def test_build_create_params_maps_model_switching_after_yaml_roundtrip() -> None:
    import yaml

    from uqadm.space.export_yaml import dump_space_snapshot_yaml
    from uqadm.space.migrate import build_create_params, plain_json_value

    class UniqueObject(dict):
        pass

    src = UniqueObject(
        {
            "name": "S",
            "fallbackModule": "fm",
            "modules": [],
            "allowModelSwitching": True,
            "switchableLanguageModels": [
                UniqueObject(
                    {
                        "object": "x",
                        "displayName": "GPT-4o",
                        "languageModel": "AZURE_GPT_4o_2024_0806",
                    }
                )
            ],
        }
    )
    snapshot = yaml.safe_load(dump_space_snapshot_yaml(plain_json_value(src)))
    params = build_create_params(snapshot)
    assert params["allowModelSwitching"] is True
    assert params["switchableLanguageModels"] == [
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
    ]


def test_build_create_params_preserves_clean_migrate_model_list() -> None:
    from uqadm.space.migrate import build_create_params, build_update_kwargs

    models = [
        {
            "displayName": "GPT-4o",
            "languageModel": "AZURE_GPT_4o_2024_0806",
            "temperature": 0.0,
        },
        {
            "displayName": "Gemini",
            "languageModel": {"name": "litellm:gemini-2-5-pro", "provider": "litellm"},
            "additionalLLMOptions": {
                "chat_template_kwargs": {"enable_thinking": False}
            },
        },
    ]
    src = {
        "name": "S",
        "fallbackModule": "fm",
        "modules": [],
        "allowModelSwitching": True,
        "switchableLanguageModels": models,
    }
    create_params = build_create_params(src)
    update_kwargs = build_update_kwargs(src)
    assert create_params["switchableLanguageModels"] == models
    assert update_kwargs["switchableLanguageModels"] == models


def test_migrate_and_export_upsert_emit_same_model_switching_params() -> None:
    import yaml

    from uqadm.space.export_yaml import dump_space_snapshot_yaml
    from uqadm.space.migrate import (
        build_create_params,
        build_update_kwargs,
        plain_json_value,
    )

    class UniqueObject(dict):
        pass

    live_src = UniqueObject(
        {
            "name": "S",
            "fallbackModule": "fm",
            "modules": [],
            "allowModelSwitching": True,
            "switchableLanguageModels": [
                UniqueObject(
                    {
                        "displayName": "GPT-4o",
                        "languageModel": "AZURE_GPT_4o_2024_0806",
                        "temperature": 0.3,
                    }
                ),
                UniqueObject(
                    {
                        "displayName": "Gemini",
                        "languageModel": UniqueObject(
                            {"name": "litellm:gemini-2-5-pro"}
                        ),
                        "additionalLLMOptions": UniqueObject(
                            {"chat_template_kwargs": {"enable_thinking": False}}
                        ),
                    }
                ),
            ],
        }
    )
    snapshot = yaml.safe_load(dump_space_snapshot_yaml(plain_json_value(live_src)))
    migrate_create = build_create_params(live_src)
    upsert_create = build_create_params(snapshot)
    migrate_update = build_update_kwargs(live_src)
    upsert_update = build_update_kwargs(snapshot)
    assert migrate_create["allowModelSwitching"] == upsert_create["allowModelSwitching"]
    assert (
        migrate_create["switchableLanguageModels"]
        == upsert_create["switchableLanguageModels"]
    )
    assert migrate_update["allowModelSwitching"] == upsert_update["allowModelSwitching"]
    assert (
        migrate_update["switchableLanguageModels"]
        == upsert_update["switchableLanguageModels"]
    )
    assert migrate_create["switchableLanguageModels"] == [
        {
            "displayName": "GPT-4o",
            "languageModel": "AZURE_GPT_4o_2024_0806",
            "temperature": 0.3,
        },
        {
            "displayName": "Gemini",
            "languageModel": {"name": "litellm:gemini-2-5-pro"},
            "additionalLLMOptions": {
                "chat_template_kwargs": {"enable_thinking": False}
            },
        },
    ]


def test_build_create_params_forwards_model_list_without_toggle() -> None:
    from uqadm.space.migrate import build_create_params

    params = build_create_params(
        {
            "name": "S",
            "fallbackModule": "fm",
            "modules": [],
            "switchableLanguageModels": [
                {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
            ],
        }
    )
    assert "allowModelSwitching" not in params
    assert params["switchableLanguageModels"] == [
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
    ]


def test_build_update_kwargs_forwards_model_list_without_toggle() -> None:
    from uqadm.space.migrate import build_update_kwargs

    kwargs = build_update_kwargs(
        {
            "name": "S",
            "switchableLanguageModels": [
                {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
            ],
        }
    )
    assert "allowModelSwitching" not in kwargs
    assert kwargs["switchableLanguageModels"] == [
        {"displayName": "GPT-4o", "languageModel": "AZURE_GPT_4o_2024_0806"},
    ]


def test_build_create_params_syncs_model_list_when_toggle_present() -> None:
    from uqadm.space.migrate import build_create_params

    params = build_create_params(
        {
            "name": "S",
            "fallbackModule": "fm",
            "modules": [],
            "allowModelSwitching": True,
            "switchableLanguageModels": None,
        }
    )
    assert params["allowModelSwitching"] is True
    assert params["switchableLanguageModels"] == []


def test_build_update_kwargs_includes_model_switching_and_allows_false() -> None:
    from uqadm.space.migrate import build_update_kwargs

    kwargs = build_update_kwargs(
        {
            "name": "S",
            "allowModelSwitching": False,
            "switchableLanguageModels": [],
        }
    )
    assert kwargs["allowModelSwitching"] is False
    assert kwargs["switchableLanguageModels"] == []


def test_build_update_kwargs_syncs_model_list_when_toggle_present() -> None:
    from uqadm.space.migrate import build_update_kwargs

    kwargs = build_update_kwargs({"name": "S", "allowModelSwitching": True})
    assert kwargs["allowModelSwitching"] is True
    assert kwargs["switchableLanguageModels"] == []


def test_build_create_params_forwards_sub_agent_fields() -> None:
    from uqadm.space.migrate import build_create_params

    params = build_create_params(
        {
            "name": "S",
            "fallbackModule": "fm",
            "modules": [],
            "isSubAgent": True,
            "subAgentSettings": {"maxIterations": 3},
        }
    )
    assert params["isSubAgent"] is True
    assert params["subAgentSettings"] == {"maxIterations": 3}


def test_build_create_params_skips_absent_sub_agent_fields() -> None:
    from uqadm.space.migrate import build_create_params

    params = build_create_params({"name": "S", "fallbackModule": "fm", "modules": []})
    assert "isSubAgent" not in params
    assert "subAgentSettings" not in params


def test_build_update_kwargs_forwards_sub_agent_fields() -> None:
    from uqadm.space.migrate import build_update_kwargs

    kwargs = build_update_kwargs(
        {
            "name": "S",
            "isSubAgent": True,
            "subAgentSettings": {"maxIterations": 3},
        }
    )
    assert kwargs["isSubAgent"] is True
    assert kwargs["subAgentSettings"] == {"maxIterations": 3}


def test_build_update_kwargs_skips_absent_sub_agent_fields() -> None:
    from uqadm.space.migrate import build_update_kwargs

    kwargs = build_update_kwargs({"name": "S"})
    assert "isSubAgent" not in kwargs
    assert "subAgentSettings" not in kwargs


def test_emit_snapshot_warnings_notes_sub_agent_settings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from uqadm.space.upsert import _emit_snapshot_warnings

    _emit_snapshot_warnings({"name": "S", "subAgentSettings": {"maxIterations": 3}})
    err = capsys.readouterr().err
    assert "sub-agent settings" in err


def test_emit_snapshot_warnings_silent_without_sub_agent_settings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from uqadm.space.upsert import _emit_snapshot_warnings

    _emit_snapshot_warnings({"name": "S"})
    err = capsys.readouterr().err
    assert "sub-agent settings" not in err
