"""Tests for Jinja2 prompt template rendering.

Each test class covers one template or call site. Tests render the template with
controlled inputs and assert on the *string content* of the output — no LLM calls
are made.

Why this matters: ``jinja2.Template.render()`` silently renders missing variables as
empty strings and silently discards extra variables. These tests are the only runtime
safety net that catches template variable mismatches before they produce degraded LLM
output.
"""

import pytest
from unique_toolkit._common.utils.jinja.render import render_template

from unique_web_search.services.content_processing.processing_strategies.llm_guard_judge import (
    JudgeAndSanitizeResponse,
    JudgeResponse,
    LLMGuardResponse,
)
from unique_web_search.services.content_processing.processing_strategies.llm_keyword_redact import (
    KeywordRedactResponse,
)
from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcessorConfig,
)
from unique_web_search.services.content_processing.processing_strategies.prompts import (
    DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE,
    DEFAULT_JUDGE_PROMPT_TEMPLATE,
    DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE,
    DEFAULT_PAGE_CONTEXT_TEMPLATE,
    DEFAULT_SANITIZE_RULES,
    DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    DEFAULT_USER_PROMPT_TEMPLATE,
)
from unique_web_search.services.content_processing.processing_strategies.schema import (
    LLMProcessorResponse,
)
from unique_web_search.services.search_engine.schema import WebSearchResult

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_page() -> WebSearchResult:
    return WebSearchResult(
        url="https://example.com/test-page",
        title="Test Page Title",
        snippet="This is the test page snippet.",
        content="This is the full test page content with enough text to be processed.",
    )


@pytest.fixture
def fake_sanitize_rules() -> str:
    return DEFAULT_SANITIZE_RULES


@pytest.fixture
def fake_config(fake_sanitize_rules: str) -> LLMProcessorConfig:
    return LLMProcessorConfig()


# ---------------------------------------------------------------------------
# system_prompt.j2
# ---------------------------------------------------------------------------


class TestSystemPromptTemplate:
    """Tests for system_prompt.j2 rendered at every call site."""

    def test_sanitize_true__includes_sanitize_rules(
        self, fake_sanitize_rules: str
    ) -> None:
        """sanitize_rules content must appear in output when sanitize=True."""
        rendered = render_template(
            DEFAULT_SYSTEM_PROMPT_TEMPLATE,
            sanitize=True,
            sanitize_rules=fake_sanitize_rules,
            output_schema={},
        )
        # A distinctive phrase from sanitize_rules.j2
        assert "GDPR Art. 9" in rendered
        assert fake_sanitize_rules in rendered

    def test_sanitize_true__includes_output_schema(self) -> None:
        """output_schema JSON must appear in output when sanitize=True."""
        schema = {"type": "object", "sentinel_key": "sentinel_value_abc123"}
        rendered = render_template(
            DEFAULT_SYSTEM_PROMPT_TEMPLATE,
            sanitize=True,
            sanitize_rules="rules",
            output_schema=schema,
        )
        assert "sentinel_value_abc123" in rendered

    def test_sanitize_false__omits_sanitize_rules_section(
        self, fake_sanitize_rules: str
    ) -> None:
        """The sanitization rules section must be absent when sanitize=False."""
        rendered = render_template(
            DEFAULT_SYSTEM_PROMPT_TEMPLATE,
            sanitize=False,
            sanitize_rules=fake_sanitize_rules,
            output_schema={},
        )
        assert "MANDATORY" not in rendered
        assert "GDPR" not in rendered

    def test_sanitize_false__includes_output_schema(self) -> None:
        """output_schema JSON must appear in output when sanitize=False."""
        schema = {"type": "object", "sentinel_key": "schema_no_sanitize_xyz"}
        rendered = render_template(
            DEFAULT_SYSTEM_PROMPT_TEMPLATE,
            sanitize=False,
            sanitize_rules="rules",
            output_schema=schema,
        )
        assert "schema_no_sanitize_xyz" in rendered

    def test_sanitize_true__references_sanitized_snippet_not_snippet(self) -> None:
        """The prompt must instruct the LLM to fill sanitized_snippet, not snippet."""
        rendered = render_template(
            DEFAULT_SYSTEM_PROMPT_TEMPLATE,
            sanitize=True,
            sanitize_rules="rules",
            output_schema={},
        )
        assert "sanitized_snippet" in rendered
        assert "sanitized_summary" in rendered

    def test_sanitize_true__does_not_reference_redaction_map(self) -> None:
        """The removed redaction_map section must not appear in output."""
        rendered = render_template(
            DEFAULT_SYSTEM_PROMPT_TEMPLATE,
            sanitize=True,
            sanitize_rules="rules",
            output_schema={},
        )
        assert "redaction_map" not in rendered

    def test_sanitize_true__includes_output_field_priority_section(self) -> None:
        """The Output Field Priority section must be present to guide chain-of-thought."""
        rendered = render_template(
            DEFAULT_SYSTEM_PROMPT_TEMPLATE,
            sanitize=True,
            sanitize_rules="rules",
            output_schema={},
        )
        assert "Output Field Priority" in rendered


# ---------------------------------------------------------------------------
# user_prompt.j2
# ---------------------------------------------------------------------------


class TestUserPromptTemplate:
    """Tests for user_prompt.j2 rendered at _run_summarize, sanitize_page, judge_and_sanitize."""

    def test_includes_query(self, fake_page: WebSearchResult) -> None:
        """query must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="unique_query_sentinel_xyz",
            sanitize=False,
        )
        assert "unique_query_sentinel_xyz" in rendered

    def test_includes_page_title(self, fake_page: WebSearchResult) -> None:
        """page.title must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="test query",
            sanitize=False,
        )
        assert fake_page.title in rendered

    def test_includes_page_url(self, fake_page: WebSearchResult) -> None:
        """page.url must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="test query",
            sanitize=False,
        )
        assert fake_page.url in rendered

    def test_includes_page_snippet(self, fake_page: WebSearchResult) -> None:
        """page.snippet must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="test query",
            sanitize=False,
        )
        assert fake_page.snippet in rendered

    def test_includes_page_content(self, fake_page: WebSearchResult) -> None:
        """page.content must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="test query",
            sanitize=False,
        )
        assert fake_page.content in rendered

    def test_sanitize_true__includes_reminder_block(
        self, fake_page: WebSearchResult
    ) -> None:
        """The sanitize REMINDER block must appear when sanitize=True."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="test query",
            sanitize=True,
        )
        assert "REMINDER" in rendered

    def test_sanitize_false__omits_reminder_block(
        self, fake_page: WebSearchResult
    ) -> None:
        """The sanitize REMINDER block must be absent when sanitize=False."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="test query",
            sanitize=False,
        )
        assert "REMINDER" not in rendered

    def test_no_objective_variable(self, fake_page: WebSearchResult) -> None:
        """objective must not appear as a placeholder in the template (it has been removed)."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="test query",
            sanitize=False,
        )
        assert "objective" not in rendered.lower() or "Objective:" not in rendered

    def test_sanitize_true__references_sanitized_fields_in_reminder(
        self, fake_page: WebSearchResult
    ) -> None:
        """The reminder block should reference sanitized_snippet/sanitized_summary, not snippet/summary."""
        rendered = render_template(
            DEFAULT_USER_PROMPT_TEMPLATE,
            page=fake_page,
            query="test query",
            sanitize=True,
        )
        assert "sanitized_snippet" in rendered or "sanitized_summary" in rendered


# ---------------------------------------------------------------------------
# judge_prompt.j2
# ---------------------------------------------------------------------------


class TestJudgePromptTemplate:
    """Tests for judge_prompt.j2 used in judge_only() calls."""

    def test_includes_output_schema(self) -> None:
        """output_schema JSON must appear in rendered output."""
        schema = {"sentinel": "judge_schema_abc456"}
        rendered = render_template(
            DEFAULT_JUDGE_PROMPT_TEMPLATE,
            sanitize_rules=DEFAULT_SANITIZE_RULES,
            output_schema=schema,
        )
        assert "judge_schema_abc456" in rendered

    def test_includes_sanitize_rules(self) -> None:
        """sanitize_rules must appear in rendered output (regression: was previously hardcoded)."""
        custom_rules = "CUSTOM_SANITIZE_RULE_SENTINEL_XYZ"
        rendered = render_template(
            DEFAULT_JUDGE_PROMPT_TEMPLATE,
            sanitize_rules=custom_rules,
            output_schema={},
        )
        assert custom_rules in rendered

    def test_default_sanitize_rules_appear_when_passed(self) -> None:
        """The default sanitize_rules content should appear when passed to judge_prompt."""
        rendered = render_template(
            DEFAULT_JUDGE_PROMPT_TEMPLATE,
            sanitize_rules=DEFAULT_SANITIZE_RULES,
            output_schema={},
        )
        assert "RedactHealth" in rendered

    def test_includes_output_field_priority_section(self) -> None:
        """The Output Field Priority section must guide chain-of-thought for reasoning."""
        rendered = render_template(
            DEFAULT_JUDGE_PROMPT_TEMPLATE,
            sanitize_rules="rules",
            output_schema={},
        )
        assert "Output Field Priority" in rendered


# ---------------------------------------------------------------------------
# judge_and_sanitize_prompt.j2
# ---------------------------------------------------------------------------


class TestJudgeAndSanitizePromptTemplate:
    """Tests for judge_and_sanitize_prompt.j2 used in judge_and_sanitize() calls."""

    def test_includes_sanitize_rules(self) -> None:
        """sanitize_rules must appear in rendered output."""
        custom_rules = "CUSTOM_JUDGE_AND_SANITIZE_RULE_SENTINEL"
        rendered = render_template(
            DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE,
            sanitize_rules=custom_rules,
            output_schema={},
        )
        assert custom_rules in rendered

    def test_includes_output_schema(self) -> None:
        """output_schema JSON must appear in rendered output."""
        schema = {"sentinel": "judge_and_sanitize_schema_789"}
        rendered = render_template(
            DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE,
            sanitize_rules="rules",
            output_schema=schema,
        )
        assert "judge_and_sanitize_schema_789" in rendered

    def test_mentions_needs_sanitization_field(self) -> None:
        """The prompt must explicitly instruct the LLM to fill needs_sanitization."""
        rendered = render_template(
            DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE,
            sanitize_rules="rules",
            output_schema={},
        )
        assert "needs_sanitization" in rendered

    def test_mentions_classification_task(self) -> None:
        """The prompt must describe the classification task (Task 1)."""
        rendered = render_template(
            DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE,
            sanitize_rules="rules",
            output_schema={},
        )
        assert "Classify" in rendered or "classify" in rendered

    def test_includes_output_field_priority_section(self) -> None:
        """The Output Field Priority section must guide chain-of-thought ordering."""
        rendered = render_template(
            DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE,
            sanitize_rules="rules",
            output_schema={},
        )
        assert "Output Field Priority" in rendered


# ---------------------------------------------------------------------------
# page_context.j2
# ---------------------------------------------------------------------------


class TestPageContextTemplate:
    """Tests for page_context.j2 used in judge_only() and LLMKeywordRedact calls."""

    def test_includes_query(self, fake_page: WebSearchResult) -> None:
        """query must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_PAGE_CONTEXT_TEMPLATE,
            page=fake_page,
            query="unique_context_query_sentinel",
        )
        assert "unique_context_query_sentinel" in rendered

    def test_includes_page_title(self, fake_page: WebSearchResult) -> None:
        """page.title must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_PAGE_CONTEXT_TEMPLATE,
            page=fake_page,
            query="test",
        )
        assert fake_page.title in rendered

    def test_includes_page_url(self, fake_page: WebSearchResult) -> None:
        """page.url must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_PAGE_CONTEXT_TEMPLATE,
            page=fake_page,
            query="test",
        )
        assert fake_page.url in rendered

    def test_includes_page_snippet(self, fake_page: WebSearchResult) -> None:
        """page.snippet must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_PAGE_CONTEXT_TEMPLATE,
            page=fake_page,
            query="test",
        )
        assert fake_page.snippet in rendered

    def test_includes_page_content(self, fake_page: WebSearchResult) -> None:
        """page.content must appear in the rendered prompt."""
        rendered = render_template(
            DEFAULT_PAGE_CONTEXT_TEMPLATE,
            page=fake_page,
            query="test",
        )
        assert fake_page.content in rendered

    def test_task_description_shown_when_passed(
        self, fake_page: WebSearchResult
    ) -> None:
        """task_description must appear in output when provided."""
        rendered = render_template(
            DEFAULT_PAGE_CONTEXT_TEMPLATE,
            page=fake_page,
            query="test",
            task_description="UNIQUE_TASK_DESC_SENTINEL",
        )
        assert "UNIQUE_TASK_DESC_SENTINEL" in rendered

    def test_task_description_absent_when_not_passed(
        self, fake_page: WebSearchResult
    ) -> None:
        """task_description must not appear (or render as empty) when not provided."""
        rendered = render_template(
            DEFAULT_PAGE_CONTEXT_TEMPLATE,
            page=fake_page,
            query="test",
        )
        assert "UNIQUE_TASK_DESC_SENTINEL" not in rendered

    def test_no_objective_in_output(self, fake_page: WebSearchResult) -> None:
        """objective has been removed from page_context.j2; no objective placeholder should render."""
        rendered = render_template(
            DEFAULT_PAGE_CONTEXT_TEMPLATE,
            page=fake_page,
            query="test",
        )
        assert "Objective:" not in rendered


# ---------------------------------------------------------------------------
# keyword_extract_prompt.j2
# ---------------------------------------------------------------------------


class TestKeywordExtractPromptTemplate:
    """Tests for keyword_extract_prompt.j2 used in LLMKeywordRedact calls."""

    def test_includes_sanitize_rules(self) -> None:
        """sanitize_rules must appear in rendered output."""
        custom_rules = "CUSTOM_KEYWORD_RULE_SENTINEL_ABC"
        rendered = render_template(
            DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE,
            sanitize_rules=custom_rules,
            output_schema={},
        )
        assert custom_rules in rendered

    def test_includes_output_schema(self) -> None:
        """output_schema JSON must appear in rendered output."""
        schema = {"sentinel": "keyword_schema_sentinel_XYZ"}
        rendered = render_template(
            DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE,
            sanitize_rules="rules",
            output_schema=schema,
        )
        assert "keyword_schema_sentinel_XYZ" in rendered


# ---------------------------------------------------------------------------
# Response model field ordering tests
# ---------------------------------------------------------------------------


class TestResponseModelFieldOrdering:
    """Tests that Pydantic response models have fields in chain-of-thought order.

    Field order in Pydantic determines JSON schema property order, which the LLM
    processes sequentially. reasoning must come first to enable chain-of-thought.
    """

    def test_llm_guard_response__reasoning_is_first_field(self) -> None:
        """LLMGuardResponse: reasoning must be the first declared field."""
        fields = list(LLMGuardResponse.model_fields.keys())
        assert fields[0] == "reasoning", (
            f"Expected 'reasoning' as first field, got '{fields[0]}'. "
            f"Full order: {fields}"
        )

    def test_llm_guard_response__field_order(self) -> None:
        """LLMGuardResponse: must have exactly reasoning, sanitized_snippet, sanitized_summary."""
        fields = list(LLMGuardResponse.model_fields.keys())
        assert fields == ["reasoning", "sanitized_snippet", "sanitized_summary"], (
            f"Unexpected field order: {fields}"
        )

    def test_llm_guard_response__does_not_inherit_snippet_summary(self) -> None:
        """LLMGuardResponse must not inherit snippet/summary from LLMProcessorResponse."""
        fields = set(LLMGuardResponse.model_fields.keys())
        assert "snippet" not in fields
        assert "summary" not in fields

    def test_judge_response__reasoning_is_first_field(self) -> None:
        """JudgeResponse: reasoning must be the first declared field."""
        fields = list(JudgeResponse.model_fields.keys())
        assert fields[0] == "reasoning", (
            f"Expected 'reasoning' as first field, got '{fields[0]}'. "
            f"Full order: {fields}"
        )

    def test_judge_response__field_order(self) -> None:
        """JudgeResponse: must have exactly reasoning, needs_sanitization."""
        fields = list(JudgeResponse.model_fields.keys())
        assert fields == ["reasoning", "needs_sanitization"], (
            f"Unexpected field order: {fields}"
        )

    def test_judge_and_sanitize_response__reasoning_is_first_field(self) -> None:
        """JudgeAndSanitizeResponse: reasoning must be the first declared field."""
        fields = list(JudgeAndSanitizeResponse.model_fields.keys())
        assert fields[0] == "reasoning", (
            f"Expected 'reasoning' as first field, got '{fields[0]}'. "
            f"Full order: {fields}"
        )

    def test_judge_and_sanitize_response__field_order(self) -> None:
        """JudgeAndSanitizeResponse: must follow reasoning → needs_sanitization → sanitized_snippet → sanitized_summary."""
        fields = list(JudgeAndSanitizeResponse.model_fields.keys())
        assert fields == [
            "reasoning",
            "needs_sanitization",
            "sanitized_snippet",
            "sanitized_summary",
        ], f"Unexpected field order: {fields}"

    def test_judge_and_sanitize_response__has_apply_to_page(self) -> None:
        """JudgeAndSanitizeResponse must have apply_to_page (not rely on inheritance)."""
        assert hasattr(JudgeAndSanitizeResponse, "apply_to_page")
        assert callable(JudgeAndSanitizeResponse.apply_to_page)


# ---------------------------------------------------------------------------
# Call site integration tests
# ---------------------------------------------------------------------------


class TestCallSiteVariables:
    """Integration-level tests: render each call site's prompts end-to-end.

    These mirror exactly how each method in llm_process.py, llm_guard_judge.py
    and llm_keyword_redact.py builds its prompts, verifying no expected content
    is silently missing.
    """

    def test_summarize__system_prompt_has_output_schema(
        self, fake_config: LLMProcessorConfig, fake_page: WebSearchResult
    ) -> None:
        """_run_summarize system prompt must embed the LLMProcessorResponse schema."""
        schema = LLMProcessorResponse.model_json_schema()
        rendered = render_template(
            fake_config.prompts.system_prompt,
            sanitize=False,
            sanitize_rules=fake_config.privacy_filter.sanitize_rules,
            output_schema=schema,
        )
        assert "snippet" in rendered
        assert "summary" in rendered

    def test_summarize__user_prompt_has_query_and_page(
        self, fake_config: LLMProcessorConfig, fake_page: WebSearchResult
    ) -> None:
        """_run_summarize user prompt must contain both query and page fields."""
        rendered = render_template(
            fake_config.prompts.user_prompt,
            page=fake_page,
            query="summarize_sentinel_query",
            sanitize=False,
        )
        assert "summarize_sentinel_query" in rendered
        assert fake_page.title in rendered
        assert fake_page.url in rendered
        assert fake_page.content in rendered

    def test_sanitize_page__system_prompt_has_rules_and_schema(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """sanitize_page system prompt must embed sanitize_rules and LLMGuardResponse schema."""
        schema = LLMGuardResponse.model_json_schema()
        rendered = render_template(
            fake_config.prompts.system_prompt,
            sanitize=True,
            sanitize_rules=fake_config.privacy_filter.sanitize_rules,
            output_schema=schema,
        )
        assert "RedactHealth" in rendered
        assert "sanitized_snippet" in rendered
        assert "sanitized_summary" in rendered

    def test_sanitize_page__user_prompt_has_query_and_page(
        self, fake_config: LLMProcessorConfig, fake_page: WebSearchResult
    ) -> None:
        """sanitize_page user prompt must contain query and page fields."""
        rendered = render_template(
            fake_config.prompts.user_prompt,
            page=fake_page,
            query="sanitize_sentinel_query",
            sanitize=True,
        )
        assert "sanitize_sentinel_query" in rendered
        assert fake_page.url in rendered

    def test_judge_only__system_prompt_has_schema(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """judge_only system prompt must embed the JudgeResponse schema."""
        schema = JudgeResponse.model_json_schema()
        rendered = render_template(
            fake_config.prompts.judge_prompt,
            sanitize_rules=fake_config.privacy_filter.sanitize_rules,
            output_schema=schema,
        )
        assert "needs_sanitization" in rendered
        assert "reasoning" in rendered

    def test_judge_only__user_prompt_has_query_and_page(
        self, fake_config: LLMProcessorConfig, fake_page: WebSearchResult
    ) -> None:
        """judge_only user prompt (page_context.j2) must contain query and page fields."""
        from unique_web_search.services.content_processing.processing_strategies.llm_guard_judge import (
            _JUDGE_TASK_PREFIX,
        )

        rendered = render_template(
            fake_config.prompts.page_context_prompt,
            page=fake_page,
            query="judge_sentinel_query",
            task_description=_JUDGE_TASK_PREFIX,
        )
        assert "judge_sentinel_query" in rendered
        assert fake_page.url in rendered
        assert _JUDGE_TASK_PREFIX in rendered

    def test_judge_and_sanitize__system_prompt_has_rules_and_schema(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """judge_and_sanitize system prompt must embed rules and JudgeAndSanitizeResponse schema."""
        schema = JudgeAndSanitizeResponse.model_json_schema()
        rendered = render_template(
            fake_config.prompts.judge_and_sanitize_prompt,
            sanitize_rules=fake_config.privacy_filter.sanitize_rules,
            output_schema=schema,
        )
        assert "needs_sanitization" in rendered
        assert "reasoning" in rendered
        assert "sanitized_snippet" in rendered

    def test_judge_and_sanitize__user_prompt_has_query_and_page(
        self, fake_config: LLMProcessorConfig, fake_page: WebSearchResult
    ) -> None:
        """judge_and_sanitize user prompt must contain query and page fields."""
        rendered = render_template(
            fake_config.prompts.user_prompt,
            page=fake_page,
            query="judge_and_sanitize_sentinel_query",
            sanitize=True,
        )
        assert "judge_and_sanitize_sentinel_query" in rendered
        assert fake_page.url in rendered

    def test_keyword_redact__system_prompt_has_rules(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """LLMKeywordRedact system prompt must embed sanitize_rules."""
        schema = KeywordRedactResponse.model_json_schema()
        rendered = render_template(
            fake_config.prompts.keyword_extract_prompt,
            sanitize_rules=fake_config.privacy_filter.sanitize_rules,
            output_schema=schema,
        )
        assert "RedactHealth" in rendered

    def test_keyword_redact__user_prompt_has_query_and_page(
        self, fake_config: LLMProcessorConfig, fake_page: WebSearchResult
    ) -> None:
        """LLMKeywordRedact user prompt (page_context.j2) must contain query and page fields."""
        from unique_web_search.services.content_processing.processing_strategies.llm_keyword_redact import (
            _KEYWORD_TASK_PREFIX,
        )

        rendered = render_template(
            fake_config.prompts.page_context_prompt,
            page=fake_page,
            query="keyword_redact_sentinel_query",
            task_description=_KEYWORD_TASK_PREFIX,
        )
        assert "keyword_redact_sentinel_query" in rendered
        assert fake_page.url in rendered
        assert _KEYWORD_TASK_PREFIX in rendered


# ---------------------------------------------------------------------------
# PromptConfig field wiring tests
# ---------------------------------------------------------------------------


class TestPromptConfigFields:
    """Tests that each PromptConfig field holds the correct default template content.

    These are regression guards: if a new field is added to PromptConfig but wired
    to the wrong default constant, or if a constant is reassigned, the test fails.
    """

    def test_judge_prompt_default_matches_template_file(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """PromptConfig.judge_prompt default must equal DEFAULT_JUDGE_PROMPT_TEMPLATE."""
        assert fake_config.prompts.judge_prompt == DEFAULT_JUDGE_PROMPT_TEMPLATE

    def test_judge_and_sanitize_prompt_default_matches_template_file(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """PromptConfig.judge_and_sanitize_prompt default must equal DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE."""
        assert (
            fake_config.prompts.judge_and_sanitize_prompt
            == DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE
        )

    def test_page_context_prompt_default_matches_template_file(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """PromptConfig.page_context_prompt default must equal DEFAULT_PAGE_CONTEXT_TEMPLATE."""
        assert fake_config.prompts.page_context_prompt == DEFAULT_PAGE_CONTEXT_TEMPLATE

    def test_keyword_extract_prompt_default_matches_template_file(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """PromptConfig.keyword_extract_prompt default must equal DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE."""
        assert (
            fake_config.prompts.keyword_extract_prompt
            == DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE
        )

    def test_prompt_config_has_all_six_prompt_fields(
        self, fake_config: LLMProcessorConfig
    ) -> None:
        """PromptConfig must expose all 6 prompt template fields."""
        expected_fields = {
            "system_prompt",
            "user_prompt",
            "judge_prompt",
            "judge_and_sanitize_prompt",
            "page_context_prompt",
            "keyword_extract_prompt",
        }
        actual_fields = set(type(fake_config.prompts).model_fields.keys())
        assert actual_fields == expected_fields, (
            f"PromptConfig field mismatch.\n"
            f"  Missing: {expected_fields - actual_fields}\n"
            f"  Extra:   {actual_fields - expected_fields}"
        )
