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
    _build_subtree_metadata_filter,
    _is_markdown,
    _parse_frontmatter,
    configure_skill_tool,
    load_skills_from_knowledge_base,
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

    def test_missing_description_returns_none(self, logger: Logger) -> None:
        file_text = "---\nname: foo\n---\nbody\n"
        content = MagicMock()
        content.key = "broken.md"
        content.id = "c6"

        skill = _build_skill(content=content, file_text=file_text, logger=logger)

        assert skill is None

    def test_non_dict_frontmatter_returns_none(self, logger: Logger) -> None:
        """YAML that parses to a non-dict (e.g. a list) should be rejected."""
        file_text = "---\n- foo\n- bar\n---\nbody\n"
        content = MagicMock()
        content.key = "broken.md"
        content.id = "c7"

        skill = _build_skill(content=content, file_text=file_text, logger=logger)

        assert skill is None

    def test_invalid_yaml_falls_back_and_returns_none(self, logger: Logger) -> None:
        """Unparseable YAML frontmatter falls back to 'no frontmatter' path."""
        file_text = "---\n: : : bad yaml\n---\nbody\n"
        content = MagicMock()
        content.key = "broken.md"
        content.id = "c8"

        skill = _build_skill(content=content, file_text=file_text, logger=logger)

        assert skill is None


class TestParseFrontmatter:
    def test_no_leading_triple_dash_returns_empty(self) -> None:
        fm, body = _parse_frontmatter(text="# Heading\nbody\n")
        assert fm == {}
        assert body == "# Heading\nbody\n"

    def test_unterminated_frontmatter_returns_empty(self) -> None:
        fm, body = _parse_frontmatter(text="---\nname: foo\nno closing\n")
        assert fm == {}
        assert body == "---\nname: foo\nno closing\n"

    def test_parses_valid_frontmatter(self) -> None:
        fm, body = _parse_frontmatter(
            text="---\nname: foo\ndescription: bar\n---\nhello\n"
        )
        assert fm == {"name": "foo", "description": "bar"}
        assert body == "hello\n"

    def test_invalid_yaml_returns_empty(self) -> None:
        fm, body = _parse_frontmatter(text="---\n: : : bad\n---\nbody\n")
        assert fm == {}
        assert body == "---\n: : : bad\n---\nbody\n"

    def test_non_dict_yaml_returns_empty(self) -> None:
        fm, body = _parse_frontmatter(text="---\n- a\n- b\n---\nbody\n")
        assert fm == {}
        assert body == "---\n- a\n- b\n---\nbody\n"

    def test_inline_triple_dash_in_value_is_not_delimiter(self) -> None:
        """``---`` inside a value must not terminate the frontmatter block."""
        text = (
            "---\nname: my---skill\ndescription: uses --- internally\n---\nreal body\n"
        )
        fm, body = _parse_frontmatter(text=text)
        assert fm == {
            "name": "my---skill",
            "description": "uses --- internally",
        }
        assert body == "real body\n"

    def test_leading_dash_not_on_own_line_is_not_frontmatter(self) -> None:
        """Text starting with ``---foo`` (no newline) is not frontmatter."""
        fm, body = _parse_frontmatter(text="---not-a-delimiter\nname: foo\n---\nbody\n")
        assert fm == {}
        assert body == "---not-a-delimiter\nname: foo\n---\nbody\n"


class TestIsMarkdown:
    def test_lowercase_md(self) -> None:
        content = MagicMock()
        content.key = "readme.md"
        assert _is_markdown(content=content) is True

    def test_uppercase_md(self) -> None:
        content = MagicMock()
        content.key = "README.MD"
        assert _is_markdown(content=content) is True

    def test_non_markdown(self) -> None:
        content = MagicMock()
        content.key = "data.txt"
        assert _is_markdown(content=content) is False


class TestBuildSubtreeMetadataFilter:
    def test_single_scope_returns_single_statement(self) -> None:
        result = _build_subtree_metadata_filter(scope_ids=["scope-1"])

        assert result["operator"] == "contains"
        assert result["value"] == "uniquepathid://scope-1"
        assert result["path"] == ["folderIdPath"]

    def test_multiple_scopes_wrapped_in_or(self) -> None:
        result = _build_subtree_metadata_filter(
            scope_ids=["scope-1", "scope-2", "scope-3"]
        )

        assert "or" in result
        predicates = result["or"]
        assert len(predicates) == 3
        assert [p["value"] for p in predicates] == [
            "uniquepathid://scope-1",
            "uniquepathid://scope-2",
            "uniquepathid://scope-3",
        ]


def _fake_info(content_id: str, key: str) -> MagicMock:
    info = MagicMock()
    info.id = content_id
    info.key = key
    return info


def _paginated(infos: list[MagicMock], total: int) -> MagicMock:
    paginated = MagicMock()
    paginated.content_infos = infos
    paginated.total_count = total
    return paginated


class TestLoadSkillsFromKnowledgeBase:
    def test_empty_scope_ids_returns_empty(self, logger: Logger) -> None:
        content_service = MagicMock()
        knowledge_base_service = MagicMock()

        result = load_skills_from_knowledge_base(
            content_service=content_service,
            knowledge_base_service=knowledge_base_service,
            scope_ids=[],
            logger=logger,
        )

        assert result == {}
        knowledge_base_service.get_paginated_content_infos.assert_not_called()

    def test_pagination_error_returns_empty(self, logger: Logger) -> None:
        content_service = MagicMock()
        knowledge_base_service = MagicMock()
        knowledge_base_service.get_paginated_content_infos.side_effect = RuntimeError(
            "boom"
        )

        result = load_skills_from_knowledge_base(
            content_service=content_service,
            knowledge_base_service=knowledge_base_service,
            scope_ids=["scope-1"],
            logger=logger,
        )

        assert result == {}

    def test_no_markdown_files_returns_empty(self, logger: Logger) -> None:
        content_service = MagicMock()
        knowledge_base_service = MagicMock()
        knowledge_base_service.get_paginated_content_infos.return_value = _paginated(
            [_fake_info("c1", "foo.txt"), _fake_info("c2", "bar.pdf")],
            total=2,
        )

        result = load_skills_from_knowledge_base(
            content_service=content_service,
            knowledge_base_service=knowledge_base_service,
            scope_ids=["scope-1"],
            logger=logger,
        )

        assert result == {}
        content_service.download_content_to_bytes.assert_not_called()

    def test_download_failure_skips_entry(self, logger: Logger) -> None:
        content_service = MagicMock()
        content_service.download_content_to_bytes.side_effect = [
            RuntimeError("download failed"),
            b"---\nname: bar\ndescription: d\n---\nbody\n",
        ]
        knowledge_base_service = MagicMock()
        knowledge_base_service.get_paginated_content_infos.return_value = _paginated(
            [_fake_info("c1", "foo.md"), _fake_info("c2", "bar.md")],
            total=2,
        )

        result = load_skills_from_knowledge_base(
            content_service=content_service,
            knowledge_base_service=knowledge_base_service,
            scope_ids=["scope-1"],
            logger=logger,
        )

        assert set(result.keys()) == {"bar"}

    def test_empty_file_is_skipped(self, logger: Logger) -> None:
        content_service = MagicMock()
        content_service.download_content_to_bytes.return_value = b"   \n"
        knowledge_base_service = MagicMock()
        knowledge_base_service.get_paginated_content_infos.return_value = _paginated(
            [_fake_info("c1", "empty.md")],
            total=1,
        )

        result = load_skills_from_knowledge_base(
            content_service=content_service,
            knowledge_base_service=knowledge_base_service,
            scope_ids=["scope-1"],
            logger=logger,
        )

        assert result == {}

    def test_duplicate_names_keep_first(self, logger: Logger) -> None:
        content_service = MagicMock()
        content_service.download_content_to_bytes.side_effect = [
            b"---\nname: dup\ndescription: first\n---\nFIRST\n",
            b"---\nname: dup\ndescription: second\n---\nSECOND\n",
        ]
        knowledge_base_service = MagicMock()
        knowledge_base_service.get_paginated_content_infos.return_value = _paginated(
            [_fake_info("c1", "a.md"), _fake_info("c2", "b.md")],
            total=2,
        )

        result = load_skills_from_knowledge_base(
            content_service=content_service,
            knowledge_base_service=knowledge_base_service,
            scope_ids=["scope-1"],
            logger=logger,
        )

        assert set(result.keys()) == {"dup"}
        assert result["dup"].description == "first"
        assert result["dup"].content == "FIRST\n"

    def test_successful_load_returns_registry(self, logger: Logger) -> None:
        content_service = MagicMock()
        content_service.download_content_to_bytes.side_effect = [
            b"---\nname: foo\ndescription: d1\n---\nFOO\n",
            b"---\nname: bar\ndescription: d2\n---\nBAR\n",
        ]
        knowledge_base_service = MagicMock()
        knowledge_base_service.get_paginated_content_infos.return_value = _paginated(
            [_fake_info("c1", "foo.md"), _fake_info("c2", "bar.md")],
            total=2,
        )

        result = load_skills_from_knowledge_base(
            content_service=content_service,
            knowledge_base_service=knowledge_base_service,
            scope_ids=["scope-1"],
            logger=logger,
        )

        assert set(result.keys()) == {"foo", "bar"}
        assert result["foo"].content == "FOO\n"
        assert result["bar"].content == "BAR\n"

    def test_paginates_across_multiple_pages(self, logger: Logger) -> None:
        """Break-out condition: ``len(page) < PAGE_SIZE`` terminates the loop."""
        content_service = MagicMock()
        content_service.download_content_to_bytes.return_value = (
            b"---\nname: s\ndescription: d\n---\nBODY\n"
        )
        knowledge_base_service = MagicMock()
        page1 = _paginated(
            [_fake_info(f"c{i}", f"a{i}.md") for i in range(100)], total=150
        )
        page2 = _paginated(
            [_fake_info(f"c{i}", f"b{i}.md") for i in range(50)], total=150
        )
        knowledge_base_service.get_paginated_content_infos.side_effect = [page1, page2]

        load_skills_from_knowledge_base(
            content_service=content_service,
            knowledge_base_service=knowledge_base_service,
            scope_ids=["scope-1"],
            logger=logger,
        )

        assert knowledge_base_service.get_paginated_content_infos.call_count == 2


class TestConfigureSkillTool:
    def _build_config(
        self, *, enabled: bool, scope_ids: list[str] | None = None
    ) -> MagicMock:
        from unique_skill_tool.config import SkillToolConfig

        skill_config = SkillToolConfig(enabled=enabled, scope_ids=scope_ids or [])
        config = MagicMock()
        config.agent.experimental.skill_tool_config = skill_config
        return config

    def test_disabled_is_noop(self, logger: Logger) -> None:
        config = self._build_config(enabled=False)
        tool_manager = MagicMock()

        configure_skill_tool(
            config=config,
            event=MagicMock(),
            logger=logger,
            content_service=MagicMock(),
            tool_manager=tool_manager,
        )

        tool_manager.add_tool.assert_not_called()

    def test_enabled_without_scopes_is_noop(self, logger: Logger) -> None:
        config = self._build_config(enabled=True, scope_ids=[])
        tool_manager = MagicMock()

        configure_skill_tool(
            config=config,
            event=MagicMock(),
            logger=logger,
            content_service=MagicMock(),
            tool_manager=tool_manager,
        )

        tool_manager.add_tool.assert_not_called()

    def test_empty_registry_does_not_register_tool(
        self, logger: Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If the skill registry ends up empty (KB error, no .md files, or all
        malformed), the SkillTool must not be registered. Its system prompt
        claims HIGHEST PRIORITY and would otherwise waste iterations or
        provoke hallucinated skill names when no skills exist.
        """
        config = self._build_config(enabled=True, scope_ids=["scope-1"])
        tool_manager = MagicMock()

        import unique_orchestrator._builders.skill_setup as skill_setup

        fake_kb_service = MagicMock()
        monkeypatch.setattr(
            skill_setup,
            "KnowledgeBaseService",
            lambda **kwargs: fake_kb_service,
        )
        monkeypatch.setattr(
            skill_setup,
            "load_skills_from_knowledge_base",
            lambda **kwargs: {},
        )

        event = MagicMock()
        event.company_id = "co-1"
        event.user_id = "u-1"

        configure_skill_tool(
            config=config,
            event=event,
            logger=logger,
            content_service=MagicMock(),
            tool_manager=tool_manager,
        )

        tool_manager.add_tool.assert_not_called()

    def test_registers_tool_when_enabled_and_scoped(
        self, logger: Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config = self._build_config(enabled=True, scope_ids=["scope-1"])
        tool_manager = MagicMock()

        # Stub out the knowledge-base client so no network / auth is needed.
        import unique_orchestrator._builders.skill_setup as skill_setup

        fake_kb_service = MagicMock()
        monkeypatch.setattr(
            skill_setup,
            "KnowledgeBaseService",
            lambda **kwargs: fake_kb_service,
        )
        monkeypatch.setattr(
            skill_setup,
            "load_skills_from_knowledge_base",
            lambda **kwargs: {
                "foo": SkillDefinition(name="foo", description="d", content="c")
            },
        )

        event = MagicMock()
        event.company_id = "co-1"
        event.user_id = "u-1"

        configure_skill_tool(
            config=config,
            event=event,
            logger=logger,
            content_service=MagicMock(),
            tool_manager=tool_manager,
        )

        tool_manager.add_tool.assert_called_once()
        registered = tool_manager.add_tool.call_args.args[0]
        assert isinstance(registered, SkillTool)
        assert "foo" in registered.skill_registry
