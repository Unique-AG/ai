"""
Unit tests for unique_toolkit.agentic.claude_agent.prompts

Naming convention: test_<function>_<scenario>_<expected>
"""

from __future__ import annotations

from unique_toolkit.agentic.claude_agent.prompts import (
    PromptContext,
    answer_style,
    build_system_prompt,
    conversation_style,
    custom_instructions_section,
    history_section,
    html_rendering_instructions,
    reference_guidelines,
    system_header,
    user_metadata_section,
)

# ─────────────────────────────────────────────────────────────────────────────
# system_header
# ─────────────────────────────────────────────────────────────────────────────


class TestSystemHeader:
    def test_system_header_contains_model_and_date(self) -> None:
        result = system_header("claude-sonnet-4-20250514", "Thursday February 26, 2026")
        assert "claude-sonnet-4-20250514" in result
        assert "Thursday February 26, 2026" in result

    def test_system_header_contains_identity_line(self) -> None:
        result = system_header("any-model", "any-date")
        assert "Unique AI Chat" in result
        assert "# System" in result


# ─────────────────────────────────────────────────────────────────────────────
# user_metadata_section
# ─────────────────────────────────────────────────────────────────────────────


class TestUserMetadataSection:
    def test_user_metadata_section_empty_when_no_metadata(self) -> None:
        assert user_metadata_section(None) == ""

    def test_user_metadata_section_empty_when_empty_dict(self) -> None:
        assert user_metadata_section({}) == ""

    def test_user_metadata_section_formats_keys_correctly(self) -> None:
        result = user_metadata_section({"first_name": "Alice", "job_title": "Engineer"})
        assert "First Name: Alice" in result
        assert "Job Title: Engineer" in result

    def test_user_metadata_section_contains_header(self) -> None:
        result = user_metadata_section({"key": "value"})
        assert "# User Information" in result

    def test_user_metadata_section_underscores_replaced(self) -> None:
        result = user_metadata_section({"user_department": "Finance"})
        assert "user_department" not in result
        assert "User Department" in result


# ─────────────────────────────────────────────────────────────────────────────
# Static section constants
# ─────────────────────────────────────────────────────────────────────────────


class TestConversationStyle:
    def test_conversation_style_is_non_empty_string(self) -> None:
        result = conversation_style()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_conversation_style_contains_expected_content(self) -> None:
        result = conversation_style()
        assert "tone" in result.lower()


class TestAnswerStyle:
    def test_answer_style_is_non_empty_string(self) -> None:
        result = answer_style()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_answer_style_contains_markdown_guidance(self) -> None:
        result = answer_style()
        assert "# Answer Style" in result

    def test_answer_style_contains_formula_rendering(self) -> None:
        result = answer_style()
        assert "Formula Rendering" in result or "formula" in result.lower()


class TestReferenceGuidelines:
    def test_reference_guidelines_is_non_empty_string(self) -> None:
        result = reference_guidelines()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_reference_guidelines_contains_source_format(self) -> None:
        result = reference_guidelines()
        assert "[source0]" in result

    def test_reference_guidelines_contains_source_number_format(self) -> None:
        result = reference_guidelines()
        assert "source_number" in result or "sourceX" in result or "[source" in result


class TestHtmlRenderingInstructions:
    def test_html_rendering_is_non_empty_string(self) -> None:
        result = html_rendering_instructions()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_html_rendering_contains_htmlrendering_tag(self) -> None:
        result = html_rendering_instructions()
        assert "HtmlRendering" in result


# ─────────────────────────────────────────────────────────────────────────────
# custom_instructions_section
# ─────────────────────────────────────────────────────────────────────────────


class TestCustomInstructionsSection:
    def test_custom_instructions_section_empty_when_none(self) -> None:
        assert custom_instructions_section(None, None, "Acme") == ""

    def test_custom_instructions_section_empty_when_both_empty_strings(self) -> None:
        assert custom_instructions_section("", "", "Acme") == ""

    def test_custom_instructions_section_includes_project_name(self) -> None:
        result = custom_instructions_section("Do X", None, "Acme Corp")
        assert "Acme Corp" in result

    def test_custom_instructions_section_includes_custom_text(self) -> None:
        result = custom_instructions_section("Always reply in French.", None, "Test")
        assert "Always reply in French." in result

    def test_custom_instructions_section_combines_custom_and_user(self) -> None:
        result = custom_instructions_section("Custom text.", "User text.", "Test")
        assert "Custom text." in result
        assert "User text." in result

    def test_custom_instructions_section_user_only_when_no_custom(self) -> None:
        result = custom_instructions_section(None, "User only.", "Test")
        assert "User only." in result
        assert result != ""

    def test_custom_instructions_section_contains_header(self) -> None:
        result = custom_instructions_section("Something", None, "Test")
        assert "# SYSTEM INSTRUCTIONS CONTEXT" in result


# ─────────────────────────────────────────────────────────────────────────────
# history_section
# ─────────────────────────────────────────────────────────────────────────────


class TestHistorySection:
    def test_history_section_empty_when_no_history(self) -> None:
        assert history_section("") == ""

    def test_history_section_includes_history_text(self) -> None:
        result = history_section("User: hi\nAssistant: hello")
        assert "User: hi" in result
        assert "Assistant: hello" in result

    def test_history_section_contains_header(self) -> None:
        result = history_section("some history")
        assert "# Conversation History" in result


# ─────────────────────────────────────────────────────────────────────────────
# build_system_prompt (composer)
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildSystemPrompt:
    def _minimal_context(self) -> PromptContext:
        return PromptContext(
            model_name="claude-sonnet-4-20250514",
            date_string="Thursday February 26, 2026",
        )

    def test_build_system_prompt_minimal_context__contains_static_sections(
        self,
    ) -> None:
        result = build_system_prompt(self._minimal_context())
        assert "# System" in result
        assert "# Answer Style" in result
        assert "# Reference Guidelines" in result
        assert "HtmlRendering" in result

    def test_build_system_prompt_minimal_context__contains_model_and_date(self) -> None:
        result = build_system_prompt(self._minimal_context())
        assert "claude-sonnet-4-20250514" in result
        assert "Thursday February 26, 2026" in result

    def test_build_system_prompt_with_all_sections(self) -> None:
        context = PromptContext(
            model_name="claude-sonnet-4-20250514",
            date_string="Thursday February 26, 2026",
            user_metadata={"department": "Engineering"},
            custom_instructions="Always be concise.",
            project_name="Acme AI",
            history_text="User: hello\nAssistant: hi",
        )
        result = build_system_prompt(context)
        assert "Department: Engineering" in result
        assert "Always be concise." in result
        assert "Acme AI" in result
        assert "User: hello" in result

    def test_build_system_prompt_excludes_empty_sections(self) -> None:
        result = build_system_prompt(self._minimal_context())
        # No double blank lines from empty sections
        assert "\n\n\n" not in result

    def test_build_system_prompt_does_not_contain_tool_descriptions(self) -> None:
        result = build_system_prompt(self._minimal_context())
        # SDK handles tool descriptions — they must not appear in the system prompt
        assert "# Tools" not in result
        assert "mcp__" not in result

    def test_build_system_prompt_override_handled_in_runner_not_here(self) -> None:
        """build_system_prompt always composes — override logic lives in the runner."""
        context = self._minimal_context()
        result = build_system_prompt(context)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_system_prompt_omits_user_metadata_when_absent(self) -> None:
        result = build_system_prompt(self._minimal_context())
        assert "# User Information" not in result

    def test_build_system_prompt_omits_history_when_empty(self) -> None:
        result = build_system_prompt(self._minimal_context())
        assert "# Conversation History" not in result

    def test_build_system_prompt_omits_custom_instructions_when_none(self) -> None:
        result = build_system_prompt(self._minimal_context())
        assert "# SYSTEM INSTRUCTIONS CONTEXT" not in result
