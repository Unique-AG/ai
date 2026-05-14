"""Tests for UniqueAI._resolve_other_options().

Verifies that the highest ``reasoning_effort`` is selected across
``additional_llm_options`` from config and the ``thinking_level`` hints
declared on skills activated in the current run.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from unique_skill_tool.schemas import SkillDefinition
from unique_skill_tool.service import SkillTool


def _make_unique_ai(
    additional_llm_options: dict,
    skill_tool: SkillTool | None = None,
) -> object:
    """Build a minimal UniqueAI-like object with only the attributes used by
    ``_resolve_other_options``.  Avoids constructing the full object graph.
    """
    from unique_orchestrator.unique_ai import UniqueAI

    instance = UniqueAI.__new__(UniqueAI)
    config = MagicMock()
    config.agent.experimental.additional_llm_options = additional_llm_options

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
