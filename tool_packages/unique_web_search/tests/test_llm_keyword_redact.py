"""Tests for LLMKeywordRedact and helper functions."""

from unittest.mock import AsyncMock, Mock

import pytest

from unique_web_search.services.content_processing.processing_strategies.llm_keyword_redact import (
    KeywordRedactResponse,
    LLMKeywordRedact,
    SensitiveKeyword,
    _fuzzy_redact_pass,
    _redact_text,
)
from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcessorConfig,
    PrivacyFilterConfig,
)
from unique_web_search.services.search_engine.schema import WebSearchResult


@pytest.fixture
def fake_page() -> WebSearchResult:
    return WebSearchResult(
        url="https://example.com/patient",
        title="Patient Record",
        snippet="John has diabetes and visits the clinic regularly.",
        content="John Smith was diagnosed with Type 2 diabetes in 2021. He also has high blood pressure.",
    )


# ---------------------------------------------------------------------------
# _fuzzy_redact_pass tests
# ---------------------------------------------------------------------------


class TestFuzzyRedactPass:
    @pytest.mark.ai
    def test_empty_phrase__returns_text_unchanged(self) -> None:
        text = "Some text here."
        assert _fuzzy_redact_pass(text, "", "[REDACTED]") == text

    @pytest.mark.ai
    def test_no_match__returns_text_unchanged(self) -> None:
        text = "The weather is sunny today."
        assert _fuzzy_redact_pass(text, "diabetes mellitus", "[RedactHealth]") == text

    @pytest.mark.ai
    def test_exact_match__redacts_phrase(self) -> None:
        text = "Patient has diabetes."
        result = _fuzzy_redact_pass(text, "diabetes", "[RedactHealth]")
        assert "[RedactHealth]" in result
        assert "diabetes" not in result.replace("[RedactHealth]", "")

    @pytest.mark.ai
    def test_fuzzy_match__redacts_near_match(self) -> None:
        text = "Patient has diabtes."
        result = _fuzzy_redact_pass(text, "diabetes", "[RedactHealth]")
        assert "[RedactHealth]" in result


# ---------------------------------------------------------------------------
# _redact_text tests
# ---------------------------------------------------------------------------


class TestRedactText:
    @pytest.mark.ai
    def test_exact_regex_pass__replaces_keywords(self) -> None:
        text = "John has diabetes and high blood pressure."
        keywords = [
            SensitiveKeyword(phrase="diabetes", tag="[RedactHealth]"),
            SensitiveKeyword(phrase="high blood pressure", tag="[RedactHealth]"),
        ]
        result = _redact_text(text, keywords)
        assert "diabetes" not in result
        assert "high blood pressure" not in result
        assert result.count("[RedactHealth]") == 2

    @pytest.mark.ai
    def test_case_insensitive__regex_pass(self) -> None:
        text = "Patient has Diabetes."
        keywords = [SensitiveKeyword(phrase="diabetes", tag="[RedactHealth]")]
        result = _redact_text(text, keywords)
        assert "Diabetes" not in result
        assert "[RedactHealth]" in result

    @pytest.mark.ai
    def test_empty_keywords__returns_original(self) -> None:
        text = "No sensitive data here."
        result = _redact_text(text, [])
        assert result == text

    @pytest.mark.ai
    def test_multiple_occurrences__replaces_all(self) -> None:
        text = "diabetes is common. diabetes affects many."
        keywords = [SensitiveKeyword(phrase="diabetes", tag="[RedactHealth]")]
        result = _redact_text(text, keywords)
        assert "diabetes" not in result
        assert result.count("[RedactHealth]") == 2


# ---------------------------------------------------------------------------
# KeywordRedactResponse tests
# ---------------------------------------------------------------------------


class TestKeywordRedactResponse:
    @pytest.mark.ai
    def test_apply_to_page__redacts_content_and_snippet(
        self, fake_page: WebSearchResult
    ) -> None:
        resp = KeywordRedactResponse(
            sensitive_keywords=[
                SensitiveKeyword(phrase="diabetes", tag="[RedactHealth]"),
            ]
        )
        result = resp.apply_to_page(fake_page)
        assert "diabetes" not in result.content
        assert "diabetes" not in result.snippet
        assert "[RedactHealth]" in result.content
        assert "[RedactHealth]" in result.snippet

    @pytest.mark.ai
    def test_apply_to_page__empty_keywords__preserves_content(
        self, fake_page: WebSearchResult
    ) -> None:
        original_content = fake_page.content
        resp = KeywordRedactResponse(sensitive_keywords=[])
        result = resp.apply_to_page(fake_page)
        assert result.content == original_content


# ---------------------------------------------------------------------------
# LLMKeywordRedact end-to-end tests
# ---------------------------------------------------------------------------


class TestLLMKeywordRedact:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__extracts_and_redacts_keywords(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            privacy_filter=PrivacyFilterConfig(sanitize=True),
        )
        llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [
            Mock(
                message=Mock(
                    parsed={
                        "sensitive_keywords": [
                            {"phrase": "Type 2 diabetes", "tag": "[RedactHealth]"},
                            {"phrase": "high blood pressure", "tag": "[RedactHealth]"},
                        ]
                    }
                )
            )
        ]
        llm_service.complete_async = AsyncMock(return_value=mock_resp)

        redactor = LLMKeywordRedact(config=config, llm_service=llm_service)
        result = await redactor(page=fake_page, query="patient info")

        assert "Type 2 diabetes" not in result.content
        assert "high blood pressure" not in result.content
        assert "[RedactHealth]" in result.content
        llm_service.complete_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__no_keywords__preserves_content(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            privacy_filter=PrivacyFilterConfig(sanitize=True),
        )
        llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(parsed={"sensitive_keywords": []}))]
        llm_service.complete_async = AsyncMock(return_value=mock_resp)

        redactor = LLMKeywordRedact(config=config, llm_service=llm_service)
        original_content = fake_page.content
        result = await redactor(page=fake_page, query="patient info")

        assert result.content == original_content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__raises_when_parsed_is_none(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            privacy_filter=PrivacyFilterConfig(sanitize=True),
        )
        llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(parsed=None))]
        llm_service.complete_async = AsyncMock(return_value=mock_resp)

        redactor = LLMKeywordRedact(config=config, llm_service=llm_service)

        with pytest.raises(ValueError, match="no parsed response"):
            await redactor(page=fake_page, query="patient info")

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__missing_query__uses_empty_string(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            privacy_filter=PrivacyFilterConfig(sanitize=True),
        )
        llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(parsed={"sensitive_keywords": []}))]
        llm_service.complete_async = AsyncMock(return_value=mock_resp)

        redactor = LLMKeywordRedact(config=config, llm_service=llm_service)
        result = await redactor(page=fake_page, query="")

        assert result.content == fake_page.content
