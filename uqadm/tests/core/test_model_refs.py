"""Tests for the model-reference find/replace engine."""

from __future__ import annotations

import copy
from typing import Any

from uqadm.core.model_refs import (
    MISSING,
    ModelRef,
    find_model_refs,
    get_at_path,
    is_model_key,
    replace_model_refs,
    to_plain,
    value_matches,
    verify_replacements,
)

OLD = "AZURE_GPT_4o_2024_0806"
NEW = "AZURE_GPT_5_2025_0807"


class UndeepcopyableDict(dict[str, Any]):
    """Stands in for ``unique_sdk.UniqueObject``.

    That class is a ``dict`` subclass whose ``__deepcopy__`` dereferences a
    ``user_id`` attribute the SDK wipes after refreshing from an API response,
    so ``copy.deepcopy`` raises ``AttributeError`` on live payloads.
    """

    def __deepcopy__(self, memo: dict[int, Any]) -> UndeepcopyableDict:
        raise AttributeError("'user_id'")

    def __copy__(self) -> UndeepcopyableDict:
        raise AttributeError("'user_id'")


# --- is_model_key ---


def test_is_model_key_accepts_model_bearing_keys() -> None:
    for key in (
        "languageModel",
        "fallbackLanguageModel",
        "tokenCountingLanguageModel",
        "summarizationModel",
        "hallucinationModel",
        "userMemoryModel",
        "smallModel",
        "largeModel",
        "researchModel",
        "model",
        "modelName",
        "fallbackModel",
        "languageModelName",
        "language_model",
        "model_name",
    ):
        assert is_model_key(key), key


def test_is_model_key_rejects_denied_and_non_model_keys() -> None:
    for key in (
        "languageModelMaxInputTokens",
        "allowModelSwitching",
        "useOrchestratorLanguageModel",
        "modelSwitching",
        "switchableLanguageModels",
        "temperature",
        "name",
        "modelCard",
    ):
        assert not is_model_key(key), key


# --- value_matches ---


def test_value_matches_string_and_object_forms() -> None:
    assert value_matches(OLD, OLD)
    assert value_matches({"name": OLD, "provider": "CUSTOM"}, OLD)
    assert not value_matches(NEW, OLD)
    assert not value_matches({"name": NEW}, OLD)
    assert not value_matches(12000, OLD)
    assert not value_matches(True, OLD)


# --- find_model_refs ---


def _space_payload() -> dict[str, Any]:
    return {
        "name": f"Space using {OLD}",  # prompt-ish text must never match
        "languageModel": OLD,
        "allowModelSwitching": True,
        "switchableLanguageModels": [
            {"displayName": "GPT-4o", "languageModel": OLD},
            {"displayName": "Other", "languageModel": "OTHER_MODEL"},
        ],
        "modules": [
            {
                "id": "mod_1",
                "name": "UniqueAI",
                "configuration": {
                    "languageModel": OLD,
                    "languageModelMaxInputTokens": 128000,
                    "services": {
                        "evaluationConfig": {
                            "hallucinationConfig": {"languageModel": OLD}
                        },
                        "userMemoryConfig": {
                            "useOrchestratorLanguageModel": True,
                        },
                    },
                    "tools": [
                        {
                            "name": "InternalSearch",
                            "configuration": {
                                "chunkRelevancySortConfig": {
                                    "languageModel": OLD,
                                    "fallbackLanguageModel": "OTHER_MODEL",
                                }
                            },
                        }
                    ],
                },
            },
        ],
    }


def test_find_model_refs_collects_nested_paths() -> None:
    refs = find_model_refs(_space_payload(), OLD)
    paths = {ref.path for ref in refs}
    assert paths == {
        "languageModel",
        "switchableLanguageModels[0].languageModel",
        "modules[0].configuration.languageModel",
        "modules[0].configuration.services.evaluationConfig.hallucinationConfig.languageModel",
        "modules[0].configuration.tools[0].configuration.chunkRelevancySortConfig.languageModel",
    }


def test_find_model_refs_matches_object_form_by_name() -> None:
    payload = {"languageModel": {"name": OLD, "provider": "CUSTOM"}}
    refs = find_model_refs(payload, OLD)
    assert [ref.path for ref in refs] == ["languageModel"]


def test_find_model_refs_ignores_prompt_text_and_traps() -> None:
    payload = {
        "explanation": f"Uses {OLD} internally",
        "languageModelMaxInputTokens": OLD,  # denied key even with string value
        "modelSwitching": OLD,
        "assistantPrompts": [{"title": OLD, "prompt": f"Ask {OLD} something"}],
    }
    assert find_model_refs(payload, OLD) == []


# --- replace_model_refs ---


def test_replace_model_refs_rewrites_all_matches() -> None:
    payload = _space_payload()
    new_payload, refs = replace_model_refs(payload, OLD, NEW)
    assert len(refs) == 5
    assert new_payload["languageModel"] == NEW
    assert new_payload["switchableLanguageModels"][0]["languageModel"] == NEW
    assert new_payload["switchableLanguageModels"][1]["languageModel"] == "OTHER_MODEL"
    config = new_payload["modules"][0]["configuration"]
    assert config["languageModel"] == NEW
    assert config["languageModelMaxInputTokens"] == 128000
    assert (
        config["services"]["evaluationConfig"]["hallucinationConfig"]["languageModel"]
        == NEW
    )
    tool_config = config["tools"][0]["configuration"]["chunkRelevancySortConfig"]
    assert tool_config["languageModel"] == NEW
    assert tool_config["fallbackLanguageModel"] == "OTHER_MODEL"


def test_replace_model_refs_does_not_mutate_input() -> None:
    payload = _space_payload()
    original = copy.deepcopy(payload)
    new_payload, refs = replace_model_refs(payload, OLD, NEW)
    assert payload == original
    assert new_payload is not payload
    assert refs


def test_replace_model_refs_writes_object_value_at_every_site() -> None:
    info = {"name": NEW, "provider": "CUSTOM"}
    payload = {
        "languageModel": OLD,
        "custom": {"languageModel": {"name": OLD, "provider": "CUSTOM"}},
    }
    new_payload, refs = replace_model_refs(payload, OLD, info)
    assert len(refs) == 2
    assert new_payload["languageModel"] == info
    assert new_payload["custom"]["languageModel"] == info


def test_replace_model_refs_object_value_copied_per_site() -> None:
    info = {"name": NEW, "provider": "CUSTOM"}
    payload = {"a": {"languageModel": OLD}, "b": {"languageModel": OLD}}
    new_payload, _ = replace_model_refs(payload, OLD, info)
    first = new_payload["a"]["languageModel"]
    second = new_payload["b"]["languageModel"]
    assert first == second == info
    assert first is not second
    assert first is not info


def test_replace_model_refs_collapses_object_site_to_name() -> None:
    payload = {"languageModel": {"name": OLD, "provider": "CUSTOM"}}
    new_payload, _ = replace_model_refs(payload, OLD, NEW)
    assert new_payload["languageModel"] == NEW


def test_replace_model_refs_no_matches_returns_equal_copy() -> None:
    payload = {"languageModel": "OTHER_MODEL"}
    new_payload, refs = replace_model_refs(payload, OLD, NEW)
    assert refs == []
    assert new_payload == payload


# --- to_plain / SDK payload handling ---


def test_to_plain_rebuilds_nested_containers() -> None:
    payload = UndeepcopyableDict(
        languageModel=OLD,
        modules=[UndeepcopyableDict(id="mod_1", configuration={"languageModel": OLD})],
    )
    plain = to_plain(payload)
    assert type(plain) is dict
    assert type(plain["modules"][0]) is dict
    assert plain == {
        "languageModel": OLD,
        "modules": [{"id": "mod_1", "configuration": {"languageModel": OLD}}],
    }


def test_to_plain_leaves_scalars_and_strings_alone() -> None:
    assert to_plain("AZURE") == "AZURE"
    assert to_plain(128000) == 128000
    assert to_plain(True) is True
    assert to_plain(None) is None


def test_replace_model_refs_handles_sdk_payloads_that_reject_deepcopy() -> None:
    """Regression: ``uqadm space model-replace`` crashed on live SDK objects."""
    payload = UndeepcopyableDict(
        languageModel=OLD,
        switchableLanguageModels=[
            UndeepcopyableDict(displayName="X", languageModel=OLD)
        ],
        modules=[
            UndeepcopyableDict(
                id="mod_1",
                configuration=UndeepcopyableDict(
                    languageModel=OLD, languageModelMaxInputTokens=128000
                ),
            )
        ],
    )
    new_payload, refs = replace_model_refs(payload, OLD, NEW)
    assert len(refs) == 3
    assert new_payload["languageModel"] == NEW
    assert new_payload["switchableLanguageModels"][0]["languageModel"] == NEW
    assert new_payload["modules"][0]["configuration"]["languageModel"] == NEW
    assert new_payload["modules"][0]["configuration"][
        "languageModelMaxInputTokens"
    ] == (128000)
    assert payload["languageModel"] == OLD  # source untouched


def test_replace_model_refs_returns_plain_containers() -> None:
    payload = UndeepcopyableDict(modules=[UndeepcopyableDict(configuration={})])
    new_payload, _ = replace_model_refs(payload, OLD, NEW)
    assert type(new_payload) is dict
    assert type(new_payload["modules"]) is list
    assert type(new_payload["modules"][0]) is dict


def test_find_model_refs_handles_sdk_payloads() -> None:
    payload = UndeepcopyableDict(languageModel=OLD)
    assert [ref.path for ref in find_model_refs(payload, OLD)] == ["languageModel"]


# --- get_at_path ---


def test_get_at_path_resolves_nested_and_indexed_paths() -> None:
    payload = _space_payload()
    assert get_at_path(payload, "languageModel") == OLD
    assert get_at_path(payload, "switchableLanguageModels[1].languageModel") == (
        "OTHER_MODEL"
    )
    assert (
        get_at_path(
            payload,
            "modules[0].configuration.tools[0].configuration"
            ".chunkRelevancySortConfig.languageModel",
        )
        == OLD
    )


def test_get_at_path_returns_missing_for_absent_paths() -> None:
    payload = _space_payload()
    assert get_at_path(payload, "vttConfig.languageModel") is MISSING
    assert get_at_path(payload, "modules[5].configuration") is MISSING
    assert get_at_path(payload, "languageModel.name") is MISSING


# --- verify_replacements ---


def _config(model: str | dict[str, Any] = OLD) -> dict[str, Any]:
    return {
        "chunkMaxTokens": 1000,
        "vttConfig": {"languageModel": model},
        "metadataExtractionConfig": {"enabled": True, "languageModel": model},
    }


def test_verify_replacements_passes_when_change_landed() -> None:
    refs = [ModelRef(path="vttConfig.languageModel", value=OLD)]
    assert verify_replacements(_config(NEW), refs, NEW) == []


def test_verify_replacements_flags_still_old_value() -> None:
    refs = [ModelRef(path="vttConfig.languageModel", value=OLD)]
    failures = verify_replacements(_config(OLD), refs, NEW)
    assert failures == [f"vttConfig.languageModel: still set to {OLD!r}"]


def test_verify_replacements_flags_dropped_key() -> None:
    refs = [ModelRef(path="metadataExtractionConfig.languageModel", value=OLD)]
    config = _config(NEW)
    del config["metadataExtractionConfig"]
    failures = verify_replacements(config, refs, NEW)
    assert failures == [
        "metadataExtractionConfig.languageModel: key missing after update "
        "(dropped by API)"
    ]


def test_verify_replacements_accepts_model_info_keeping_the_old_name() -> None:
    """Rewriting a bare name into model info of that same name is a real change."""
    expected = {"name": OLD, "provider": "CUSTOM"}
    refs = [ModelRef(path="vttConfig.languageModel", value=OLD)]
    config = _config()
    config["vttConfig"]["languageModel"] = dict(expected)
    assert verify_replacements(config, refs, expected) == []


def test_verify_replacements_ignores_extra_keys_on_a_model_info_object() -> None:
    expected = {"name": NEW, "provider": "CUSTOM"}
    refs = [ModelRef(path="vttConfig.languageModel", value=OLD)]
    config = _config()
    config["vttConfig"]["languageModel"] = {**expected, "region": "westeurope"}
    assert verify_replacements(config, refs, expected) == []


def test_verify_replacements_flags_model_info_write_that_was_ignored() -> None:
    expected = {"name": OLD, "provider": "CUSTOM"}
    refs = [ModelRef(path="vttConfig.languageModel", value=OLD)]
    failures = verify_replacements(_config(OLD), refs, expected)
    assert failures == [f"vttConfig.languageModel: still set to {OLD!r}"]


def test_verify_replacements_reports_an_unexpected_value() -> None:
    refs = [ModelRef(path="vttConfig.languageModel", value=OLD)]
    failures = verify_replacements(_config("SOMETHING_ELSE"), refs, NEW)
    assert failures == [
        f"vttConfig.languageModel: expected {NEW!r}, got 'SOMETHING_ELSE'"
    ]
