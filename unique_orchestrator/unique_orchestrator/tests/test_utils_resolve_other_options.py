"""Tests for utils.resolve_other_options().

Verifies that the highest effort level is selected across
``additional_llm_options`` from config and the ``thinking_level`` hints
declared on skills activated in the current run, and that the effort is
written in the format required by the active API.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from unique_skill_tool.service import SkillTool

from unique_orchestrator.utils import resolve_other_options


def _make_config(
    additional_llm_options: dict,
    use_responses_api: bool = False,
    supported_reasoning_efforts: list[str] | None = None,
) -> MagicMock:
    config = MagicMock()
    config.agent.experimental.additional_llm_options = additional_llm_options
    config.agent.experimental.responses_api_config.use_responses_api = use_responses_api
    config.agent.experimental.use_responses_api = use_responses_api
    config.space.language_model.supported_reasoning_efforts = (
        supported_reasoning_efforts
    )
    return config


def _make_tool_manager(skill_tool: SkillTool | None = None) -> MagicMock:
    tool_manager = MagicMock()
    tool_manager.get_tool_by_name.return_value = skill_tool
    return tool_manager


def _make_skill_tool_with_max(max_level: str | None) -> SkillTool:
    tool = MagicMock(spec=SkillTool)
    tool.max_thinking_level = max_level
    return tool


def _call(
    additional_llm_options: dict,
    skill_tool: SkillTool | None = None,
    use_responses_api: bool = False,
    supported_reasoning_efforts: list[str] | None = None,
) -> dict:
    return resolve_other_options(
        config=_make_config(
            additional_llm_options, use_responses_api, supported_reasoning_efforts
        ),
        tool_manager=_make_tool_manager(skill_tool),
        logger=MagicMock(),
    )


class TestResolveOtherOptions:
    def test_returns_config_options_unchanged_when_no_skill_tool(self) -> None:
        result = _call({"temperature": 0.5})
        assert result == {"temperature": 0.5}

    def test_returns_config_options_unchanged_when_skill_tool_has_no_hint(self) -> None:
        skill_tool = _make_skill_tool_with_max(None)
        result = _call({"temperature": 0.5}, skill_tool=skill_tool)
        assert result == {"temperature": 0.5}

    def test_injects_skill_hint_when_config_has_no_reasoning_effort(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        result = _call({}, skill_tool=skill_tool)
        assert result["reasoning_effort"] == "high"

    def test_config_effort_wins_when_higher_than_skill(self) -> None:
        skill_tool = _make_skill_tool_with_max("low")
        result = _call({"reasoning_effort": "high"}, skill_tool=skill_tool)
        assert result["reasoning_effort"] == "high"

    def test_skill_hint_wins_when_higher_than_config(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        result = _call({"reasoning_effort": "low"}, skill_tool=skill_tool)
        assert result["reasoning_effort"] == "high"

    def test_equal_levels_preserved(self) -> None:
        skill_tool = _make_skill_tool_with_max("medium")
        result = _call({"reasoning_effort": "medium"}, skill_tool=skill_tool)
        assert result["reasoning_effort"] == "medium"

    def test_other_options_keys_passed_through_unchanged(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {"reasoning_effort": "low", "responseFormat": {"type": "json_object"}},
            skill_tool=skill_tool,
        )
        assert result["reasoning_effort"] == "high"
        assert result["responseFormat"] == {"type": "json_object"}

    def test_does_not_mutate_config_dict(self) -> None:
        original = {"reasoning_effort": "low"}
        skill_tool = _make_skill_tool_with_max("high")
        _call(original, skill_tool=skill_tool)
        assert original == {"reasoning_effort": "low"}

    # ── Responses API ─────────────────────────────────────────────────────────

    def test_reads_effort_from_nested_reasoning_dict_for_responses_api(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {"reasoning": {"effort": "low"}},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        assert result["reasoning"] == {"effort": "high"}
        assert "reasoning_effort" not in result

    def test_nested_effort_config_wins_when_higher_than_skill(self) -> None:
        skill_tool = _make_skill_tool_with_max("low")
        result = _call(
            {"reasoning": {"effort": "high"}},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        assert result["reasoning"] == {"effort": "high"}

    def test_skill_hint_injected_when_no_nested_effort_config(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        result = _call({}, skill_tool=skill_tool, use_responses_api=True)
        assert result["reasoning"] == {"effort": "high"}
        assert "reasoning_effort" not in result

    def test_flat_reasoning_effort_ignored_when_responses_api_active(self) -> None:
        """``reasoning_effort`` (flat) is in the wrong format for the responses API
        and must not be picked up as the config effort value."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {"reasoning_effort": "low"},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        assert result["reasoning"] == {"effort": "high"}
        assert result.get("reasoning_effort") == "low"

    def test_extra_reasoning_subkeys_preserved_for_responses_api(self) -> None:
        """Other keys inside ``reasoning`` (e.g. ``summary``) must survive."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {"reasoning": {"effort": "low", "summary": "auto"}},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        assert result["reasoning"] == {"effort": "high", "summary": "auto"}

    def test_json_string_reasoning_is_parsed_for_responses_api(self) -> None:
        """``reasoning`` stored as a JSON string must be parsed before use."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {"reasoning": '{"effort": "low"}'},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        assert result["reasoning"] == {"effort": "high"}

    def test_invalid_json_string_reasoning_treated_as_empty_for_responses_api(
        self,
    ) -> None:
        """An unparseable string must not crash; skill max is used as effort."""
        skill_tool = _make_skill_tool_with_max("medium")
        result = _call(
            {"reasoning": "not-json"},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        assert result["reasoning"] == {"effort": "medium"}

    # ── Completions API ───────────────────────────────────────────────────────

    def test_nested_reasoning_effort_ignored_when_completions_api_active(self) -> None:
        """``reasoning: {effort: ...}`` is in the wrong format for the completions API
        and must not be picked up as the config effort value."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {"reasoning": {"effort": "low"}},
            skill_tool=skill_tool,
            use_responses_api=False,
        )
        assert result["reasoning_effort"] == "high"
        assert result.get("reasoning") == {"effort": "low"}

    # ── Invalid config effort ─────────────────────────────────────────────────

    def test_unrecognised_config_effort_falls_back_to_skill_max(self) -> None:
        """An unrecognised effort string must not crash; skill max is used instead."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call({"reasoning_effort": "very_high"}, skill_tool=skill_tool)
        assert result["reasoning_effort"] == "high"

    def test_unrecognised_config_effort_passes_through_when_no_skill_max(self) -> None:
        """When no skill thinking_level is active the invalid value passes through unchanged."""
        skill_tool = _make_skill_tool_with_max(None)
        result = _call({"reasoning_effort": "very_high"}, skill_tool=skill_tool)
        assert result["reasoning_effort"] == "very_high"

    def test_unrecognised_nested_effort_falls_back_to_skill_max_responses_api(
        self,
    ) -> None:
        """Same guard for the responses-API nested path."""
        skill_tool = _make_skill_tool_with_max("medium")
        result = _call(
            {"reasoning": {"effort": "very_high"}},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        assert result["reasoning"] == {"effort": "medium"}

    # ── Supported reasoning efforts ───────────────────────────────────────────

    def test_effort_written_when_within_supported_list(self) -> None:
        """Resolved effort is written when it appears in the supported list."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {},
            skill_tool=skill_tool,
            supported_reasoning_efforts=["low", "medium", "high"],
        )
        assert result["reasoning_effort"] == "high"

    def test_effort_skipped_when_model_does_not_support_reasoning(self) -> None:
        """Empty supported list means the model does not support reasoning_effort at all."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call({}, skill_tool=skill_tool, supported_reasoning_efforts=[])
        assert "reasoning_effort" not in result

    def test_effort_skipped_when_resolved_effort_not_in_supported_list(self) -> None:
        """Resolved effort outside the supported list is not written."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {},
            skill_tool=skill_tool,
            supported_reasoning_efforts=["low"],
        )
        assert "reasoning_effort" not in result

    def test_original_options_preserved_when_effort_skipped(self) -> None:
        """Other options survive when the effort is skipped due to model constraints."""
        skill_tool = _make_skill_tool_with_max("high")
        result = _call(
            {"temperature": 0.5},
            skill_tool=skill_tool,
            supported_reasoning_efforts=[],
        )
        assert result == {"temperature": 0.5}

    # ── No effort resolved ────────────────────────────────────────────────────

    def test_no_effort_resolved_leaves_options_unchanged(self) -> None:
        """When neither config nor skill provides an effort, options pass through."""
        result = _call({"responseFormat": {"type": "json_object"}})
        assert result == {"responseFormat": {"type": "json_object"}}
        assert "reasoning_effort" not in result
        assert "reasoning" not in result
