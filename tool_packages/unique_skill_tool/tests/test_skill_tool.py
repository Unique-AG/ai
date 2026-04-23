"""Tests for the SkillTool and its prompt helpers.

Covers:
- SkillTool.run() with valid, unknown, and empty skill names
- Skill name normalization
- Tool description enum generation from skill registry
- Budget-aware skill listing (format_skill_listing)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_skill_tool.config import (
    SkillToolConfig,
)
from unique_skill_tool.schemas import (
    SkillDefinition,
)
from unique_skill_tool.service import (
    SkillTool,
)
from unique_skill_tool.utils import (
    extract_prefix_skills,
    format_skill_listing,
    get_char_budget,
    normalize_skill_name,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill",
    content: str = "Do the test thing.",
) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        description=description,
        content=content,
    )


def _make_skill_registry(*skills: SkillDefinition) -> dict[str, SkillDefinition]:
    return {s.name: s for s in skills}


def _make_tool(
    skill_registry: dict[str, SkillDefinition] | None = None,
    config: SkillToolConfig | None = None,
) -> SkillTool:
    if skill_registry is None:
        skill_registry = _make_skill_registry(_make_skill())
    if config is None:
        config = SkillToolConfig(enabled=True)

    event = MagicMock()
    return SkillTool(event=event, skill_registry=skill_registry, config=config)


def _make_tool_call(
    skill_name: str = "test-skill",
    arguments: str = "",
) -> LanguageModelFunction:
    args: dict[str, str] = {"skill_name": skill_name}
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
    async def test_valid_skill_returns_content(self) -> None:
        skill = _make_skill(content="Step 1: Do the thing.\nStep 2: Done.")
        tool = _make_tool(skill_registry=_make_skill_registry(skill))

        result = await tool.run(_make_tool_call("test-skill"))

        assert result.successful
        assert "Step 1: Do the thing." in result.content

        assert "skill_loaded" in result.content

    async def test_valid_skill_with_arguments(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call("test-skill", arguments="focus on X"))

        assert result.successful
        assert "focus on X" in result.content

    async def test_unknown_skill_returns_error(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call("nonexistent"))

        assert not result.successful
        assert "Unknown skill" in result.error_message
        assert "nonexistent" in result.error_message

    async def test_empty_skill_name_returns_error(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call(""))

        assert not result.successful
        assert "non-empty" in result.error_message

    async def test_whitespace_only_skill_name_returns_error(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call("   "))

        assert not result.successful
        assert "non-empty" in result.error_message

    async def test_leading_slash_is_normalized(self) -> None:
        tool = _make_tool()
        result = await tool.run(_make_tool_call("/test-skill"))

        assert result.successful

    async def test_error_lists_available_skills(self) -> None:
        skills = [_make_skill("alpha"), _make_skill("beta")]
        tool = _make_tool(skill_registry=_make_skill_registry(*skills))

        result = await tool.run(_make_tool_call("gamma"))

        assert "alpha" in result.error_message
        assert "beta" in result.error_message


class TestSkillToolMessageLog:
    """When a skill is loaded, a COMPLETED message log step is emitted.

    Mirrors the Internal Search tool pattern: the user sees a step in
    the assistant message log indicating which skill was activated.
    """

    async def test_valid_skill_writes_completed_message_log(self) -> None:
        skill = _make_skill("my-skill", description="Does stuff")
        tool = _make_tool(skill_registry=_make_skill_registry(skill))
        mock_logger = MagicMock()
        mock_logger.create_or_update_message_log_async = AsyncMock(
            return_value=MagicMock()
        )
        tool._message_step_logger = mock_logger

        result = await tool.run(_make_tool_call("my-skill"))

        assert result.successful
        mock_logger.create_or_update_message_log_async.assert_awaited_once()
        kwargs = mock_logger.create_or_update_message_log_async.call_args.kwargs
        assert "my-skill" in kwargs["header"]
        assert kwargs["status"] == MessageLogStatus.COMPLETED

    async def test_unknown_skill_does_not_write_message_log(self) -> None:
        tool = _make_tool()
        mock_logger = MagicMock()
        mock_logger.create_or_update_message_log_async = AsyncMock()
        tool._message_step_logger = mock_logger

        result = await tool.run(_make_tool_call("nonexistent"))

        assert not result.successful
        mock_logger.create_or_update_message_log_async.assert_not_called()

    async def test_message_log_failure_does_not_break_skill_loading(self) -> None:
        skill = _make_skill("my-skill")
        tool = _make_tool(skill_registry=_make_skill_registry(skill))
        mock_logger = MagicMock()
        mock_logger.create_or_update_message_log_async = AsyncMock(
            side_effect=RuntimeError("backend down")
        )
        tool._message_step_logger = mock_logger

        result = await tool.run(_make_tool_call("my-skill"))

        assert result.successful
        assert "skill_loaded" in result.content


# ---------------------------------------------------------------------------
# SkillTool.tool_description()
# ---------------------------------------------------------------------------


class TestSkillToolDescription:
    def test_enum_contains_skill_names(self) -> None:
        skills = [_make_skill("analyze"), _make_skill("summarize")]
        tool = _make_tool(skill_registry=_make_skill_registry(*skills))

        desc = tool.tool_description()
        params = desc.parameters
        assert isinstance(params, dict)

        enum_values = params["properties"]["skill_name"]["enum"]
        assert set(enum_values) == {"analyze", "summarize"}

    def test_empty_registry_has_no_enum(self) -> None:
        tool = _make_tool(skill_registry={})

        desc = tool.tool_description()
        params = desc.parameters
        assert isinstance(params, dict)

        assert "enum" not in params["properties"]["skill_name"]


# ---------------------------------------------------------------------------
# SkillTool.tool_description_for_system_prompt()
# ---------------------------------------------------------------------------


class TestSkillToolSystemPrompt:
    """The system prompt must NOT contain the skill listing.

    Mirrors Claude Code: the listing lives in per-turn
    ``<system-reminder>`` blocks (see :class:`TestSkillToolUserPrompt`),
    not in the static system prompt, so it cannot go stale.
    """

    def test_does_not_include_skill_listing(self) -> None:
        skills = [_make_skill("my-skill", description="Does stuff")]
        tool = _make_tool(skill_registry=_make_skill_registry(*skills))

        prompt = tool.tool_description_for_system_prompt()

        assert "my-skill" not in prompt
        assert "Does stuff" not in prompt
        assert "Available skills:" not in prompt

    def test_points_to_system_reminder(self) -> None:
        tool = _make_tool()
        prompt = tool.tool_description_for_system_prompt()

        assert "system-reminder" in prompt.lower()

    def test_empty_registry_still_static_only(self) -> None:
        tool = _make_tool(skill_registry={})
        prompt = tool.tool_description_for_system_prompt()

        assert "Available skills:" not in prompt
        assert "Execute a skill" in prompt


# ---------------------------------------------------------------------------
# SkillTool.tool_description_for_user_prompt()
# ---------------------------------------------------------------------------


class TestSkillToolUserPrompt:
    """Literal extra text appended per-turn to the user message.

    The skill listing lives in :meth:`SkillTool.tool_system_reminder_for_user_prompt`
    (see :class:`TestSkillToolSystemReminder`), NOT here. This method
    only returns ``config.tool_description_for_user_prompt`` verbatim,
    mirroring every other tool.
    """

    def test_returns_config_value_verbatim(self) -> None:
        config = SkillToolConfig(
            enabled=True,
            tool_description_for_user_prompt="extra prompt text",
        )
        tool = _make_tool(config=config)

        assert tool.tool_description_for_user_prompt() == "extra prompt text"

    def test_does_not_include_skill_listing(self) -> None:
        skills = [_make_skill("my-skill", description="Does stuff")]
        tool = _make_tool(skill_registry=_make_skill_registry(*skills))

        user_prompt = tool.tool_description_for_user_prompt()

        assert "my-skill" not in user_prompt
        assert "<system-reminder>" not in user_prompt

    def test_default_config_returns_empty(self) -> None:
        tool = _make_tool()

        assert tool.tool_description_for_user_prompt() == ""


# ---------------------------------------------------------------------------
# SkillTool.tool_system_reminder_for_user_prompt()
# ---------------------------------------------------------------------------


class TestSkillToolSystemReminder:
    """Per-turn ``<system-reminder>`` listing injected into the user message."""

    def test_includes_system_reminder_block(self) -> None:
        skills = [_make_skill("my-skill", description="Does stuff")]
        tool = _make_tool(skill_registry=_make_skill_registry(*skills))

        reminder = tool.tool_system_reminder_for_user_prompt()

        assert "<system-reminder>" in reminder
        assert "</system-reminder>" in reminder

    def test_includes_claude_code_preamble(self) -> None:
        tool = _make_tool()
        reminder = tool.tool_system_reminder_for_user_prompt()

        assert (
            "The following skills are available. "
            "Use the Skill tool to invoke them." in reminder
        )

    def test_includes_skill_listing(self) -> None:
        skills = [_make_skill("my-skill", description="Does stuff")]
        tool = _make_tool(skill_registry=_make_skill_registry(*skills))

        reminder = tool.tool_system_reminder_for_user_prompt()

        assert "- my-skill: Does stuff" in reminder

    def test_empty_registry_returns_empty_string(self) -> None:
        tool = _make_tool(skill_registry={})

        assert tool.tool_system_reminder_for_user_prompt() == ""

    def test_empty_reminder_template_returns_empty(self) -> None:
        config = SkillToolConfig(enabled=True, tool_system_reminder_for_user_message="")
        tool = _make_tool(config=config)

        assert tool.tool_system_reminder_for_user_prompt() == ""


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

    def test_description_shown_in_listing(self) -> None:
        skills = [_make_skill("x", description="Short desc. Use when you need X")]
        result = format_skill_listing(skills)

        assert "Short desc. Use when you need X" in result

    def test_descriptions_truncated_when_over_budget(self) -> None:
        long_desc = "A" * 500
        skills = [_make_skill(f"skill-{i}", description=long_desc) for i in range(20)]

        config = SkillToolConfig(skill_budget_context_percent=0.01)
        result = format_skill_listing(
            skills, context_window_tokens=50_000, config=config
        )

        for skill in skills:
            assert skill.name in result

        for line in result.split("\n"):
            assert len(line) < 500

    def test_names_only_fallback_when_extreme_budget(self) -> None:
        long_desc = "B" * 300
        skills = [_make_skill(f"s{i}", description=long_desc) for i in range(100)]

        config = SkillToolConfig(skill_budget_context_percent=0.01)
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
        assert len(desc_part) <= config.max_listing_desc_chars
        assert desc_part.endswith("...")


# ---------------------------------------------------------------------------
# extract_prefix_skills
# ---------------------------------------------------------------------------


class TestExtractPrefixSkills:
    """The matcher used by the orchestrator to preload ``/skill-name`` invocations.

    Only consecutive tokens at the very start of the message count — a
    token anywhere else is treated as normal text. Matching stops on the
    first unknown name so code samples, URLs, or prose containing ``/``
    segments are never silently swallowed.
    """

    def test_no_tokens_returns_empty_and_original(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("just a question", reg)
        assert skills == []
        assert remaining == "just a question"

    def test_single_prefix_token(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("/foo how are things?", reg)
        assert [s.name for s in skills] == ["foo"]
        assert remaining == "how are things?"

    def test_multiple_prefix_tokens(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"), _make_skill("bar"))
        skills, remaining = extract_prefix_skills("/foo /bar the rest", reg)
        assert [s.name for s in skills] == ["foo", "bar"]
        assert remaining == "the rest"

    def test_duplicate_tokens_deduped_preserving_order(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"), _make_skill("bar"))
        skills, remaining = extract_prefix_skills("/foo /bar /foo ask away", reg)
        assert [s.name for s in skills] == ["foo", "bar"]
        assert remaining == "ask away"

    def test_unknown_token_stops_matching(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("/nope /foo rest", reg)
        assert skills == []
        assert remaining == "/nope /foo rest"

    def test_known_then_unknown_keeps_known(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("/foo /nope rest", reg)
        assert [s.name for s in skills] == ["foo"]
        assert remaining == "/nope rest"

    def test_token_in_middle_is_ignored(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("please run /foo for me", reg)
        assert skills == []
        assert remaining == "please run /foo for me"

    def test_leading_whitespace_tolerated(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("   /foo  rest", reg)
        assert [s.name for s in skills] == ["foo"]
        assert remaining == "rest"

    def test_token_alone_returns_empty_remainder(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("/foo", reg)
        assert [s.name for s in skills] == ["foo"]
        assert remaining == ""

    def test_hyphenated_name_not_partially_matched(self) -> None:
        """``/foo-bar`` must not match a skill called ``foo``.

        The regex is greedy on ``[A-Za-z0-9_-]*`` so it captures
        ``foo-bar`` as one token; registry lookup then fails and
        matching stops without advancing.
        """
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("/foo-bar rest", reg)
        assert skills == []
        assert remaining == "/foo-bar rest"

    def test_hyphenated_name_matches_registered_skill(self) -> None:
        reg = _make_skill_registry(_make_skill("foo-bar"))
        skills, remaining = extract_prefix_skills("/foo-bar rest", reg)
        assert [s.name for s in skills] == ["foo-bar"]
        assert remaining == "rest"

    def test_empty_input(self) -> None:
        reg = _make_skill_registry(_make_skill("foo"))
        skills, remaining = extract_prefix_skills("", reg)
        assert skills == []
        assert remaining == ""

    def test_empty_registry(self) -> None:
        skills, remaining = extract_prefix_skills("/foo hi", {})
        assert skills == []
        assert remaining == "/foo hi"

    def test_name_starting_with_digit_is_matched(self) -> None:
        """Schema allows names starting with digits (e.g. ``5-forces``)."""
        reg = _make_skill_registry(_make_skill("5-forces"))
        skills, remaining = extract_prefix_skills("/5-forces rest", reg)
        assert [s.name for s in skills] == ["5-forces"]
        assert remaining == "rest"

    def test_all_digits_name_is_matched(self) -> None:
        reg = _make_skill_registry(_make_skill("123"))
        skills, remaining = extract_prefix_skills("/123 rest", reg)
        assert [s.name for s in skills] == ["123"]
        assert remaining == "rest"
