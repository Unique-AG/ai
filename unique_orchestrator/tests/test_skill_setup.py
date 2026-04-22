"""Tests for the preload_invoked_skills helper.

The preloader runs before the first LLM iteration. When the user message
starts with ``/skill-name`` tokens, it activates each matching skill via
the exact same path the model would take mid-loop (SkillTool.run +
history_manager.add_tool_call_results), and returns the user message
with the matched ``/skill-name`` tokens stripped so the caller can
render the turn showing only the actual query.
"""

from __future__ import annotations

from logging import Logger
from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_skill_tool.schemas import SkillDefinition
from unique_skill_tool.service import SkillTool
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_orchestrator._builders.skill_setup import (
    _build_skill,
    preload_invoked_skills,
)


def _make_skill(name: str, content: str = "skill body") -> SkillDefinition:
    return SkillDefinition(name=name, description="desc", content=content)


def _make_event(text: str) -> MagicMock:
    event = MagicMock()
    event.payload.user_message.text = text
    return event


class _FakeToolManager:
    def __init__(self, skill_tool: SkillTool | None) -> None:
        self._skill_tool = skill_tool

    def get_tool_by_name(self, name: str) -> SkillTool | None:
        if self._skill_tool is not None and name == self._skill_tool.name:
            return self._skill_tool
        return None


def _make_skill_tool(skills: list[SkillDefinition]) -> SkillTool:
    registry = {s.name: s for s in skills}
    tool = SkillTool.__new__(SkillTool)
    tool._skill_registry = registry  # type: ignore[attr-defined]
    tool._message_step_logger = MagicMock()  # type: ignore[attr-defined]
    tool._message_step_logger.create_or_update_message_log_async = AsyncMock(
        return_value=MagicMock()
    )
    tool.logger = MagicMock()  # type: ignore[attr-defined]
    return tool


@pytest.fixture
def logger() -> Logger:
    return MagicMock(spec=Logger)


class TestPreloadInvokedSkills:
    @pytest.mark.asyncio
    async def test_noop_when_skill_tool_not_registered(self, logger: Logger) -> None:
        event = _make_event("/foo question")
        history_manager = MagicMock()
        tool_manager = _FakeToolManager(skill_tool=None)

        stripped_text = await preload_invoked_skills(
            event=event,
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
        )

        assert stripped_text is None
        history_manager.add_tool_call.assert_not_called()
        history_manager._append_tool_calls_to_history.assert_not_called()
        history_manager.add_tool_call_results.assert_not_called()

    @pytest.mark.asyncio
    async def test_noop_when_no_tokens(self, logger: Logger) -> None:
        event = _make_event("just a normal question")
        history_manager = MagicMock()
        skill_tool = _make_skill_tool([_make_skill("foo")])
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        stripped_text = await preload_invoked_skills(
            event=event,
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
        )

        assert stripped_text is None
        history_manager.add_tool_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_skill_preloaded(self, logger: Logger) -> None:
        event = _make_event("/foo what are the revenue trends?")
        history_manager = MagicMock()
        skill_tool = _make_skill_tool([_make_skill("foo", content="FOO BODY")])
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        stripped_text = await preload_invoked_skills(
            event=event,
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
        )

        assert stripped_text == "what are the revenue trends?"

        history_manager.add_tool_call.assert_called_once()
        synthetic_call = history_manager.add_tool_call.call_args.args[0]
        assert isinstance(synthetic_call, LanguageModelFunction)
        assert synthetic_call.name == SkillTool.name
        assert synthetic_call.arguments == {"skill_name": "foo"}

        history_manager._append_tool_calls_to_history.assert_called_once()
        appended = history_manager._append_tool_calls_to_history.call_args.args[0]
        assert appended == [synthetic_call]

        history_manager.add_tool_call_results.assert_called_once()
        responses = history_manager.add_tool_call_results.call_args.args[0]
        assert len(responses) == 1
        response = responses[0]
        assert isinstance(response, ToolCallResponse)
        assert response.name == SkillTool.name
        assert response.id == synthetic_call.id
        assert "FOO BODY" in response.content
        assert "<skill_loaded>foo</skill_loaded>" in response.content

    @pytest.mark.asyncio
    async def test_multiple_skills_preloaded_in_order(self, logger: Logger) -> None:
        event = _make_event("/foo /bar tell me more")
        history_manager = MagicMock()
        skill_tool = _make_skill_tool(
            [_make_skill("foo", content="FOO"), _make_skill("bar", content="BAR")]
        )
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        stripped_text = await preload_invoked_skills(
            event=event,
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
        )

        assert stripped_text == "tell me more"

        assert history_manager.add_tool_call.call_count == 2
        call_args = [c.args[0] for c in history_manager.add_tool_call.call_args_list]
        assert [c.arguments["skill_name"] for c in call_args] == ["foo", "bar"]

        appended = history_manager._append_tool_calls_to_history.call_args.args[0]
        assert len(appended) == 2
        assert [c.arguments["skill_name"] for c in appended] == ["foo", "bar"]

        responses = history_manager.add_tool_call_results.call_args.args[0]
        assert [r.id for r in responses] == [c.id for c in appended]
        assert "FOO" in responses[0].content
        assert "BAR" in responses[1].content

    @pytest.mark.asyncio
    async def test_unknown_prefix_noop(self, logger: Logger) -> None:
        event = _make_event("/unknown /foo question")
        history_manager = MagicMock()
        skill_tool = _make_skill_tool([_make_skill("foo")])
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        stripped_text = await preload_invoked_skills(
            event=event,
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
        )

        assert stripped_text is None
        assert event.payload.user_message.text == "/unknown /foo question"
        history_manager.add_tool_call.assert_not_called()


class TestBuildSkill:
    def test_parses_frontmatter_and_body(self, logger: Logger) -> None:
        file_text = (
            "---\n"
            "name: summarize\n"
            "description: Summarize a document.\n"
            "---\n"
            "\n"
            "# Summarize\n"
            "Do the thing.\n"
        )
        content = MagicMock()
        content.key = "summarize.md"
        content.id = "c1"

        skill = _build_skill(content=content, file_text=file_text, logger=logger)

        assert skill is not None
        assert skill.name == "summarize"
        assert skill.description == "Summarize a document."
        assert skill.content == "# Summarize\nDo the thing.\n"

    def test_empty_body_does_not_leak_frontmatter(self, logger: Logger) -> None:
        """Regression: when the body after frontmatter is empty, we must not
        fall back to the raw file text — that would inject the YAML
        frontmatter (``---\\nname: ...\\n---``) into the skill prompt.
        """
        file_text = "---\nname: empty\ndescription: An empty skill.\n---\n"
        content = MagicMock()
        content.key = "empty.md"
        content.id = "c2"

        skill = _build_skill(content=content, file_text=file_text, logger=logger)

        assert skill is not None
        assert skill.name == "empty"
        assert skill.content == ""
        assert "---" not in skill.content
        assert "name:" not in skill.content

    def test_missing_name_returns_none(self, logger: Logger) -> None:
        file_text = "---\ndescription: No name here.\n---\nbody\n"
        content = MagicMock()
        content.key = "broken.md"
        content.id = "c3"

        skill = _build_skill(content=content, file_text=file_text, logger=logger)

        assert skill is None

    def test_no_frontmatter_returns_none(self, logger: Logger) -> None:
        file_text = "# Just a markdown file\nwith no frontmatter.\n"
        content = MagicMock()
        content.key = "plain.md"
        content.id = "c4"

        skill = _build_skill(content=content, file_text=file_text, logger=logger)

        assert skill is None

    def test_empty_file_returns_none(self, logger: Logger) -> None:
        content = MagicMock()
        content.key = "empty.md"
        content.id = "c5"

        skill = _build_skill(content=content, file_text="   \n\n", logger=logger)

        assert skill is None
