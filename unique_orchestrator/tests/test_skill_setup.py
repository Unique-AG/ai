"""Tests for skill setup and preload helpers."""

from __future__ import annotations

from logging import Logger
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unique_skill_tool.schemas import SelectableSkill, SkillDefinition
from unique_skill_tool.service import SkillTool
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.app.schemas import ChatEventSkillChoice
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_orchestrator._builders.skill_setup import (
    _build_skill,
    _parse_frontmatter,
    configure_skill_tool,
    load_selectable_skills,
    preload_invoked_skills,
)


def _make_skill(
    name: str,
    content: str = "skill body",
) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        description="desc",
        content=content,
    )


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
        history_manager = MagicMock()
        tool_manager = _FakeToolManager(skill_tool=None)

        await preload_invoked_skills(
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
            skill_choices=[],
        )

        history_manager.add_tool_call.assert_not_called()
        history_manager._append_tool_calls_to_history.assert_not_called()
        history_manager.add_tool_call_results.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_skill_preloaded(self, logger: Logger) -> None:
        history_manager = MagicMock()
        skill_tool = _make_skill_tool([_make_skill("foo", content="FOO BODY")])
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        await preload_invoked_skills(
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
            skill_choices=[SelectableSkill(name="foo", content_id="cid-1")],
        )

        history_manager.add_tool_call.assert_called_once()
        synthetic_call = history_manager.add_tool_call.call_args.args[0]
        assert isinstance(synthetic_call, LanguageModelFunction)
        assert synthetic_call.name == SkillTool.name
        assert synthetic_call.arguments == {"skill_name": "foo"}

        history_manager.add_tool_call_results.assert_called_once()
        responses = history_manager.add_tool_call_results.call_args.args[0]
        assert len(responses) == 1
        response = responses[0]
        assert isinstance(response, ToolCallResponse)
        assert "FOO BODY" in response.content

    @pytest.mark.asyncio
    async def test_forced_skill_choice_preloaded_without_slash_token(
        self, logger: Logger
    ) -> None:
        history_manager = MagicMock()
        skill_tool = _make_skill_tool([_make_skill("foo", content="FOO BODY")])
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        await preload_invoked_skills(
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
            skill_choices=[SelectableSkill(name="foo", content_id="cid-1")],
        )

        history_manager.add_tool_call.assert_called_once()
        synthetic_call = history_manager.add_tool_call.call_args.args[0]
        assert isinstance(synthetic_call, LanguageModelFunction)
        assert synthetic_call.arguments == {"skill_name": "foo"}

    @pytest.mark.asyncio
    async def test_slash_tokens_in_message_do_not_preload_without_skill_choices(
        self, logger: Logger
    ) -> None:
        history_manager = MagicMock()
        skill_tool = _make_skill_tool([_make_skill("foo", content="FOO BODY")])
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        await preload_invoked_skills(
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
            skill_choices=[],
        )

        history_manager.add_tool_call.assert_not_called()
        history_manager._append_tool_calls_to_history.assert_not_called()
        history_manager.add_tool_call_results.assert_not_called()

    @pytest.mark.asyncio
    async def test_forced_skill_choice_by_content_id_without_name(
        self, logger: Logger
    ) -> None:
        history_manager = MagicMock()
        skill_tool = _make_skill_tool(
            [_make_skill("foo", content="FOO BODY")]
        )
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        await preload_invoked_skills(
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
            skill_choices=[SelectableSkill(name="", content_id="cid-1")],
        )

        history_manager.add_tool_call.assert_called_once()
        synthetic_call = history_manager.add_tool_call.call_args.args[0]
        assert isinstance(synthetic_call, LanguageModelFunction)
        assert synthetic_call.arguments == {"skill_name": "foo"}

    @pytest.mark.asyncio
    async def test_duplicate_skill_choices_preload_once(self, logger: Logger) -> None:
        history_manager = MagicMock()
        skill_tool = _make_skill_tool([_make_skill("foo", content="FOO BODY")])
        tool_manager = _FakeToolManager(skill_tool=skill_tool)

        await preload_invoked_skills(
            tool_manager=tool_manager,  # type: ignore[arg-type]
            history_manager=history_manager,
            logger=logger,
            skill_choices=[
                SelectableSkill(name="foo", content_id="cid-1"),
                SelectableSkill(name="/foo", content_id="cid-2"),
                SelectableSkill(name="foo", content_id="cid-3"),
            ],
        )

        history_manager.add_tool_call.assert_called_once()


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

        skill = _build_skill(
            content_id="c1",
            content_key="summarize.md",
            file_text=file_text,
            logger=logger,
        )

        assert skill is not None
        assert skill.name == "summarize"
        assert skill.description == "Summarize a document."
        assert skill.content == "# Summarize\nDo the thing."


class TestParseFrontmatter:
    def test_parses_valid_frontmatter(self) -> None:
        fm, body = _parse_frontmatter(
            text="---\nname: foo\ndescription: bar\n---\nhello\n"
        )
        assert fm == {"name": "foo", "description": "bar"}
        assert body == "hello"


class TestLoadSelectableSkills:
    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, logger: Logger) -> None:
        content_service = MagicMock()
        content_service.download_content_to_bytes_async = AsyncMock()

        result = await load_selectable_skills(
            content_service=content_service,
            selectable_skills=[],
            logger=logger,
        )

        assert result == {}
        content_service.download_content_to_bytes_async.assert_not_awaited()


class TestConfigureSkillTool:
    def _build_config(
        self,
        *,
        is_enabled: bool | None,
        selectable_skills: list[SelectableSkill] | None = None,
    ) -> MagicMock:
        from unique_skill_tool.config import SkillSelection, SkillToolConfig
        from unique_toolkit.agentic.tools.config import ToolBuildConfig

        tools: list[ToolBuildConfig] = []
        if is_enabled is not None:
            tools.append(
                ToolBuildConfig(
                    name=SkillTool.name,
                    configuration=SkillToolConfig(
                        selectable_skills=SkillSelection(
                            selected=selectable_skills or [],
                        ),
                    ),
                    is_enabled=is_enabled,
                )
            )

        config = MagicMock()
        config.space.tools = tools
        return config

    def _make_skill_tool(self) -> SkillTool:
        tool = SkillTool.__new__(SkillTool)
        tool._skill_registry = {}  # type: ignore[attr-defined]
        return tool

    @pytest.mark.asyncio
    async def test_enabled_without_available_skills_excludes_tool(
        self, logger: Logger
    ) -> None:
        config = self._build_config(is_enabled=True, selectable_skills=[])
        tool_manager = MagicMock()

        await configure_skill_tool(
            config=config,
            logger=logger,
            content_service=MagicMock(),
            tool_manager=tool_manager,
        )

        tool_manager.exclude_tool.assert_called_once_with(SkillTool.name)
        tool_manager.get_tool_by_name.assert_not_called()

    @pytest.mark.asyncio
    async def test_space_selectables_ignored_without_available_skills(
        self, logger: Logger
    ) -> None:
        selectable_skills = [SelectableSkill(content_id="cid-1", name="Skill 1")]
        config = self._build_config(
            is_enabled=True, selectable_skills=selectable_skills
        )
        tool_manager = MagicMock()
        content_service = MagicMock()

        with patch(
            "unique_orchestrator._builders.skill_setup.load_selectable_skills",
            new=AsyncMock(return_value={}),
        ) as mock_load_selectable_skills:
            await configure_skill_tool(
                config=config,
                logger=logger,
                content_service=content_service,
                tool_manager=tool_manager,
            )

        mock_load_selectable_skills.assert_not_called()
        tool_manager.exclude_tool.assert_called_once_with(SkillTool.name)
        tool_manager.get_tool_by_name.assert_not_called()

    @pytest.mark.asyncio
    async def test_enabled_with_available_skills_populates_tool_registry(
        self, logger: Logger
    ) -> None:
        config = self._build_config(
            is_enabled=True,
            selectable_skills=[
                SelectableSkill(content_id="space-only", name="Ignored in space"),
            ],
        )
        content_service = MagicMock()
        tool_manager = MagicMock()
        skill_tool = self._make_skill_tool()
        tool_manager.get_tool_by_name.return_value = skill_tool
        expected_registry = {"foo": _make_skill("foo", content="skill content")}
        from_message = [
            ChatEventSkillChoice(content_id="cid-1", scope_id="", name="Skill 1")
        ]
        expected_selectable = [
            SelectableSkill(name="Skill 1", scope_id="", content_id="cid-1")
        ]

        with patch(
            "unique_orchestrator._builders.skill_setup.load_selectable_skills",
            new=AsyncMock(return_value=expected_registry),
        ) as mock_load_selectable_skills:
            await configure_skill_tool(
                config=config,
                logger=logger,
                content_service=content_service,
                tool_manager=tool_manager,
                available_skills=from_message,
            )

        mock_load_selectable_skills.assert_awaited_once_with(
            content_service=content_service,
            selectable_skills=expected_selectable,
            logger=logger,
        )
        assert skill_tool.skill_registry == expected_registry
        tool_manager.exclude_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_enabled_with_multiple_available_skills_loads_full_registry(
        self, logger: Logger
    ) -> None:
        config = self._build_config(is_enabled=True, selectable_skills=[])
        content_service = MagicMock()
        tool_manager = MagicMock()
        skill_tool = self._make_skill_tool()
        tool_manager.get_tool_by_name.return_value = skill_tool
        from_message = [
            ChatEventSkillChoice(content_id="cid-1", scope_id="", name="Skill 1"),
            ChatEventSkillChoice(content_id="cid-2", scope_id="", name="Skill 2"),
        ]
        expected_selectable = [
            SelectableSkill(name="Skill 1", scope_id="", content_id="cid-1"),
            SelectableSkill(name="Skill 2", scope_id="", content_id="cid-2"),
        ]
        expected_registry = {
            "foo": _make_skill("foo", content="skill content"),
            "bar": _make_skill("bar", content="other skill content"),
        }

        with patch(
            "unique_orchestrator._builders.skill_setup.load_selectable_skills",
            new=AsyncMock(return_value=expected_registry),
        ) as mock_load_selectable_skills:
            await configure_skill_tool(
                config=config,
                logger=logger,
                content_service=content_service,
                tool_manager=tool_manager,
                available_skills=from_message,
            )

        mock_load_selectable_skills.assert_awaited_once_with(
            content_service=content_service,
            selectable_skills=expected_selectable,
            logger=logger,
        )
        assert skill_tool.skill_registry == expected_registry
        tool_manager.exclude_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_enabled_with_single_available_skill_loads_registry(
        self, logger: Logger
    ) -> None:
        config = self._build_config(is_enabled=True, selectable_skills=[])
        content_service = MagicMock()
        tool_manager = MagicMock()
        skill_tool = self._make_skill_tool()
        tool_manager.get_tool_by_name.return_value = skill_tool
        from_message = [
            ChatEventSkillChoice(content_id="cid-1", scope_id="", name="Skill 1")
        ]
        expected_selectable = [
            SelectableSkill(name="Skill 1", scope_id="", content_id="cid-1")
        ]
        expected_registry = {"foo": _make_skill("foo", content="skill content")}

        with patch(
            "unique_orchestrator._builders.skill_setup.load_selectable_skills",
            new=AsyncMock(return_value=expected_registry),
        ) as mock_load_selectable_skills:
            await configure_skill_tool(
                config=config,
                logger=logger,
                content_service=content_service,
                tool_manager=tool_manager,
                available_skills=from_message,
            )

        mock_load_selectable_skills.assert_awaited_once_with(
            content_service=content_service,
            selectable_skills=expected_selectable,
            logger=logger,
        )
        assert skill_tool.skill_registry == expected_registry
        tool_manager.exclude_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_available_skills_only_source_space_selectables_ignored(
        self, logger: Logger
    ) -> None:
        config = self._build_config(
            is_enabled=True,
            selectable_skills=[
                SelectableSkill(content_id="space-only", name="Space skill"),
            ],
        )
        content_service = MagicMock()
        tool_manager = MagicMock()
        skill_tool = self._make_skill_tool()
        tool_manager.get_tool_by_name.return_value = skill_tool
        from_message = [
            ChatEventSkillChoice(
                content_id="cid-msg",
                scope_id="scope_1",
                name="",
            )
        ]
        expected_merged = [
            SelectableSkill(
                name="",
                scope_id="scope_1",
                content_id="cid-msg",
            )
        ]
        expected_registry = {"foo": _make_skill("foo", content="skill content")}

        with patch(
            "unique_orchestrator._builders.skill_setup.load_selectable_skills",
            new=AsyncMock(return_value=expected_registry),
        ) as mock_load_selectable_skills:
            await configure_skill_tool(
                config=config,
                logger=logger,
                content_service=content_service,
                tool_manager=tool_manager,
                available_skills=from_message,
            )

        mock_load_selectable_skills.assert_awaited_once_with(
            content_service=content_service,
            selectable_skills=expected_merged,
            logger=logger,
        )
        assert skill_tool.skill_registry == expected_registry
        tool_manager.exclude_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_available_skills_empty_registry_after_load_excludes_tool(
        self, logger: Logger
    ) -> None:
        from_message = [
            ChatEventSkillChoice(content_id="cid-1", scope_id="", name="Skill 1")
        ]
        config = self._build_config(is_enabled=True, selectable_skills=[])
        tool_manager = MagicMock()
        content_service = MagicMock()

        with patch(
            "unique_orchestrator._builders.skill_setup.load_selectable_skills",
            new=AsyncMock(return_value={}),
        ) as mock_load_selectable_skills:
            await configure_skill_tool(
                config=config,
                logger=logger,
                content_service=content_service,
                tool_manager=tool_manager,
                available_skills=from_message,
            )

        mock_load_selectable_skills.assert_awaited_once()
        tool_manager.exclude_tool.assert_called_once_with(SkillTool.name)
        tool_manager.get_tool_by_name.assert_not_called()
