"""Tests for UniqueAI._resolve_other_options().

Verifies that the highest effort level is selected across
``additional_llm_options`` from config and the ``thinking_level`` hints
declared on skills activated in the current run, and that the effort is
written in the format required by the active API.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from unique_skill_tool.schemas import SkillDefinition
from unique_skill_tool.service import SkillTool


def _make_unique_ai(
    additional_llm_options: dict,
    skill_tool: SkillTool | None = None,
    use_responses_api: bool = False,
) -> object:
    """Build a minimal UniqueAI-like object with only the attributes used by
    ``_resolve_other_options``.  Avoids constructing the full object graph.
    """
    from unique_orchestrator.unique_ai import UniqueAI

    instance = UniqueAI.__new__(UniqueAI)
    config = MagicMock()
    config.agent.experimental.additional_llm_options = additional_llm_options
    config.agent.experimental.responses_api_config.use_responses_api = use_responses_api
    config.agent.experimental.use_responses_api = use_responses_api

    tool_manager = MagicMock()
    tool_manager.get_tool_by_name.return_value = skill_tool

    instance._config = config  # type: ignore[attr-defined]
    instance._tool_manager = tool_manager  # type: ignore[attr-defined]
    return instance


def _make_skill_tool_with_max(max_level: str | None) -> SkillTool:
    """Return a SkillTool whose max_thinking_level is stubbed."""
    tool = MagicMock(spec=SkillTool)
    tool.max_thinking_level = max_level
    return tool


class TestResolveOtherOptions:
    def test_returns_config_options_unchanged_when_no_skill_tool(self) -> None:
        ai = _make_unique_ai({"temperature": 0.5})
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result == {"temperature": 0.5}

    def test_returns_config_options_unchanged_when_skill_tool_has_no_hint(
        self,
    ) -> None:
        skill_tool = _make_skill_tool_with_max(None)
        ai = _make_unique_ai({"temperature": 0.5}, skill_tool=skill_tool)
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result == {"temperature": 0.5}

    def test_injects_skill_hint_when_config_has_no_reasoning_effort(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai({}, skill_tool=skill_tool)
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning_effort"] == "high"

    def test_config_effort_wins_when_higher_than_skill(self) -> None:
        skill_tool = _make_skill_tool_with_max("low")
        ai = _make_unique_ai({"reasoning_effort": "high"}, skill_tool=skill_tool)
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning_effort"] == "high"

    def test_skill_hint_wins_when_higher_than_config(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai({"reasoning_effort": "low"}, skill_tool=skill_tool)
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning_effort"] == "high"

    def test_equal_levels_preserved(self) -> None:
        skill_tool = _make_skill_tool_with_max("medium")
        ai = _make_unique_ai({"reasoning_effort": "medium"}, skill_tool=skill_tool)
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning_effort"] == "medium"

    def test_other_options_keys_passed_through_unchanged(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai(
            {"reasoning_effort": "low", "responseFormat": {"type": "json_object"}},
            skill_tool=skill_tool,
        )
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning_effort"] == "high"
        assert result["responseFormat"] == {"type": "json_object"}

    def test_does_not_mutate_config_dict(self) -> None:
        original = {"reasoning_effort": "low"}
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai(original, skill_tool=skill_tool)
        ai._resolve_other_options()  # type: ignore[attr-defined]
        assert original == {"reasoning_effort": "low"}

    # ── Responses API ─────────────────────────────────────────────────────────

    def test_reads_effort_from_nested_reasoning_dict_for_responses_api(self) -> None:
        """``reasoning: {effort: ...}`` is the expected format for the responses API."""
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai(
            {"reasoning": {"effort": "low"}},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning"] == {"effort": "high"}
        assert "reasoning_effort" not in result

    def test_nested_effort_config_wins_when_higher_than_skill(self) -> None:
        skill_tool = _make_skill_tool_with_max("low")
        ai = _make_unique_ai(
            {"reasoning": {"effort": "high"}},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning"] == {"effort": "high"}

    def test_skill_hint_injected_when_no_nested_effort_config(self) -> None:
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai({}, skill_tool=skill_tool, use_responses_api=True)
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning"] == {"effort": "high"}
        assert "reasoning_effort" not in result

    def test_flat_reasoning_effort_ignored_when_responses_api_active(self) -> None:
        """``reasoning_effort`` (flat) is in the wrong format for the responses API
        and must not be picked up as the config effort value."""
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai(
            {"reasoning_effort": "low"},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning"] == {"effort": "high"}
        assert result.get("reasoning_effort") == "low"  # passed through untouched

    def test_extra_reasoning_subkeys_preserved_for_responses_api(self) -> None:
        """Other keys inside ``reasoning`` (e.g. ``summary``) must survive."""
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai(
            {"reasoning": {"effort": "low", "summary": "auto"}},
            skill_tool=skill_tool,
            use_responses_api=True,
        )
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning"] == {"effort": "high", "summary": "auto"}

    # ── Completions API ───────────────────────────────────────────────────────

    def test_nested_reasoning_effort_ignored_when_completions_api_active(self) -> None:
        """``reasoning: {effort: ...}`` is in the wrong format for the completions API
        and must not be picked up as the config effort value."""
        skill_tool = _make_skill_tool_with_max("high")
        ai = _make_unique_ai(
            {"reasoning": {"effort": "low"}},
            skill_tool=skill_tool,
            use_responses_api=False,
        )
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result["reasoning_effort"] == "high"
        assert result.get("reasoning") == {"effort": "low"}  # passed through untouched

    # ── No effort resolved ────────────────────────────────────────────────────

    def test_no_effort_resolved_leaves_options_unchanged(self) -> None:
        """When neither config nor skill provides an effort, options pass through."""
        ai = _make_unique_ai({"responseFormat": {"type": "json_object"}})
        result = ai._resolve_other_options()  # type: ignore[attr-defined]
        assert result == {"responseFormat": {"type": "json_object"}}
        assert "reasoning_effort" not in result
        assert "reasoning" not in result
