"""Tests for the experimental SkillTool and its prompt helpers.

Covers:
- SkillTool.run() with valid, unknown, and empty skill names
- Skill name normalization
- Tool description enum generation from registry
- Budget-aware skill listing (format_skill_listing)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unique_toolkit.agentic.tools.experimental.skill_tool.config import (
    SkillToolConfig,
)
from unique_toolkit.agentic.tools.experimental.skill_tool.prompt import (
    MIN_DESC_LENGTH,
    format_skill_listing,
    get_char_budget,
)
from unique_toolkit.agentic.tools.experimental.skill_tool.schemas import (
    SkillDefinition,
)
from unique_toolkit.agentic.tools.experimental.skill_tool.tool import (
    SkillTool,
    normalize_skill_name,
)
from unique_toolkit.language_model.schemas import LanguageModelFunction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill",
    when_to_use: str = "",
    content: str = "Do the test thing.",
) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        description=description,
        when_to_use=when_to_use,
        content=content,
    )


def _make_registry(*skills: SkillDefinition) -> dict[str, SkillDefinition]:
    return {s.name: s for s in skills}


def _make_tool(
    registry: dict[str, SkillDefinition] | None = None,
    config: SkillToolConfig | None = None,
) -> SkillTool:
    if registry is None:
        registry = _make_registry(_make_skill())
    if config is None:
        config = SkillToolConfig(enabled=True)

    event = MagicMock()
    return SkillTool(event=event, registry=registry, config=config)


def _make_tool_call(
    skill_name: str = "test-skill",
    arguments: str = "",
) -> LanguageModelFunction:
    args: dict = {"skill_name": skill_name}
    if arguments:
        args["arguments"] = arguments
    return LanguageModelFunction(name="Skill", arguments=args)


# ---------------------------------------------------------------------------
# normalize_skill_name
# ---------------------------------------------------------------------------


class TestNormalizeSkillName:
    def test_strips_whitespace(self) -> None:
        assert normalize_skill_name("  my-skill  ") == "my-skill"

    def test_strips_leading_slash(self) -> None:
        assert normalize_skill_name("/my-skill") == "my-skill"

    def test_strips_slash_and_whitespace(self) -> None:
        assert normalize_skill_name("  /my-skill  ") == "my-skill"

    def test_no_op_for_clean_name(self) -> None:
        assert normalize_skill_name("my-skill") == "my-skill"


# ---------------------------------------------------------------------------
# SkillTool.run()
# ---------------------------------------------------------------------------


class TestSkillToolRun:
    @pytest.mark.asyncio
    async def test_valid_skill_returns_content(self) -> None:
        skill = _make_skill(content="Step 1: Do the thing.\nStep 2: Done.")
        tool = _make_tool(registry=_make_registry(skill))

        result = await tool.run(_make_tool_call("test-skill"))

        assert result.successful
        assert "Step 1: Do the thing." in result.content
        assert "skill_loaded" in result.content

    @pytest.mark.asyncio
    async def test_valid_skill_with_arguments(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call("test-skill", arguments="focus on X"))

        assert result.successful
        assert "focus on X" in result.content

    @pytest.mark.asyncio
    async def test_unknown_skill_returns_error(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call("nonexistent"))

        assert not result.successful
        assert "Unknown skill" in result.error_message
        assert "nonexistent" in result.error_message

    @pytest.mark.asyncio
    async def test_empty_skill_name_returns_error(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call(""))

        assert not result.successful
        assert "non-empty" in result.error_message

    @pytest.mark.asyncio
    async def test_whitespace_only_skill_name_returns_error(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call("   "))

        assert not result.successful
        assert "non-empty" in result.error_message

    @pytest.mark.asyncio
    async def test_leading_slash_is_normalized(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call("/test-skill"))

        assert result.successful

    @pytest.mark.asyncio
    async def test_error_lists_available_skills(self) -> None:
        skills = [_make_skill("alpha"), _make_skill("beta")]
        tool = _make_tool(registry=_make_registry(*skills))

        result = await tool.run(_make_tool_call("gamma"))

        assert "alpha" in result.error_message
        assert "beta" in result.error_message


# ---------------------------------------------------------------------------
# SkillTool.tool_description()
# ---------------------------------------------------------------------------


class TestSkillToolDescription:
    def test_enum_contains_skill_names(self) -> None:
        skills = [_make_skill("analyze"), _make_skill("summarize")]
        tool = _make_tool(registry=_make_registry(*skills))

        desc = tool.tool_description()
        params = desc.parameters
        assert isinstance(params, dict)

        enum_values = params["properties"]["skill_name"]["enum"]
        assert set(enum_values) == {"analyze", "summarize"}

    def test_empty_registry_has_no_enum(self) -> None:
        tool = _make_tool(registry={})

        desc = tool.tool_description()
        params = desc.parameters
        assert isinstance(params, dict)

        assert "enum" not in params["properties"]["skill_name"]


# ---------------------------------------------------------------------------
# SkillTool.tool_description_for_system_prompt()
# ---------------------------------------------------------------------------


class TestSkillToolSystemPrompt:
    def test_includes_skill_listing(self) -> None:
        skills = [_make_skill("my-skill", description="Does stuff")]
        tool = _make_tool(registry=_make_registry(*skills))

        prompt = tool.tool_description_for_system_prompt()

        assert "Available skills:" in prompt
        assert "my-skill" in prompt
        assert "Does stuff" in prompt

    def test_empty_registry_no_listing(self) -> None:
        tool = _make_tool(registry={})
        prompt = tool.tool_description_for_system_prompt()

        assert "Available skills:" not in prompt


# ---------------------------------------------------------------------------
# get_char_budget
# ---------------------------------------------------------------------------


class TestGetCharBudget:
    def test_default_fallback(self) -> None:
        config = SkillToolConfig()
        assert get_char_budget(None, config) == 8_000

    def test_context_window_based(self) -> None:
        config = SkillToolConfig(skill_budget_context_percent=0.01)
        budget = get_char_budget(200_000, config)
        assert budget == 200_000 * 4 * 0.01

    def test_custom_percent(self) -> None:
        config = SkillToolConfig(skill_budget_context_percent=0.05)
        budget = get_char_budget(100_000, config)
        assert budget == 100_000 * 4 * 0.05


# ---------------------------------------------------------------------------
# format_skill_listing
# ---------------------------------------------------------------------------


class TestFormatSkillListing:
    def test_empty_skills(self) -> None:
        assert format_skill_listing([]) == ""

    def test_single_skill_within_budget(self) -> None:
        skills = [_make_skill("my-skill", description="Does things")]
        result = format_skill_listing(skills)

        assert result == "- my-skill: Does things"

    def test_when_to_use_appended(self) -> None:
        skills = [
            _make_skill("x", description="Short desc", when_to_use="When you need X")
        ]
        result = format_skill_listing(skills)

        assert "Short desc - When you need X" in result

    def test_descriptions_truncated_when_over_budget(self) -> None:
        long_desc = "A" * 500
        skills = [_make_skill(f"skill-{i}", description=long_desc) for i in range(20)]

        config = SkillToolConfig(skill_budget_context_percent=0.001)
        result = format_skill_listing(
            skills, context_window_tokens=10_000, config=config
        )

        for skill in skills:
            assert skill.name in result

        for line in result.split("\n"):
            assert len(line) < 500

    def test_names_only_fallback_when_extreme_budget(self) -> None:
        long_desc = "B" * 300
        skills = [_make_skill(f"s{i}", description=long_desc) for i in range(100)]

        config = SkillToolConfig(skill_budget_context_percent=0.001)
        result = format_skill_listing(
            skills, context_window_tokens=1_000, config=config
        )

        for skill in skills:
            assert f"- {skill.name}" in result

        assert ":" not in result.replace("- ", "")

    def test_description_capped_at_max_listing_desc_chars(self) -> None:
        long_desc = "C" * 400
        skills = [_make_skill("x", description=long_desc)]
        config = SkillToolConfig(max_listing_desc_chars=100)

        result = format_skill_listing(skills, config=config)

        desc_part = result.split(": ", 1)[1]
        assert len(desc_part) <= 100
        assert desc_part.endswith("\u2026")
