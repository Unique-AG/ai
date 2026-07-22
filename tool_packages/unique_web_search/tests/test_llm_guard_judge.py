"""Tests for LLMGuardJudge and its response models."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_web_search.schema import WebSearchDebugInfo
from unique_web_search.services.content_processing.processing_strategies.llm_guard_judge import (
    JudgeAndSanitizeResponse,
    LLMGuardJudge,
    LLMGuardResponse,
)
from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcessorConfig,
    PrivacyFilterConfig,
)
from unique_web_search.services.content_processing.processing_strategies.settings import (
    SanitizeMode,
)
from unique_web_search.services.search_engine.schema import WebSearchResult


@pytest.fixture
def fake_page() -> WebSearchResult:
    return WebSearchResult(
        url="https://example.com/test",
        title="Test Page",
        snippet="Original snippet",
        content="Original content with some text.",
    )


@pytest.fixture
def fake_query() -> str:
    return "test search query"


FLAG_MESSAGE = "SENSITIVE CONTENT FLAGGED"


def _make_config(
    sanitize_mode: SanitizeMode = SanitizeMode.ALWAYS_SANITIZE,
) -> LLMProcessorConfig:
    return LLMProcessorConfig(
        enabled=True,
        privacy_filter=PrivacyFilterConfig(
            sanitize=True,
            sanitize_mode=sanitize_mode,
            flag_message=FLAG_MESSAGE,
        ),
    )


def _mock_llm_service(
    parsed_response: dict, usage: LanguageModelTokenUsage | None = None
) -> Mock:
    service = Mock()
    mock_resp = Mock()
    mock_resp.choices = [Mock(message=Mock(parsed=parsed_response))]
    mock_resp.usage = usage
    service.complete_async = AsyncMock(return_value=mock_resp)
    return service


# ---------------------------------------------------------------------------
# LLMGuardResponse tests
# ---------------------------------------------------------------------------


class TestLLMGuardResponse:
    @pytest.mark.ai
    def test_apply_to_page__sets_content_and_snippet(
        self, fake_page: WebSearchResult
    ) -> None:
        resp = LLMGuardResponse(
            reasoning="No sensitive data found.",
            sanitized_content="Cleaned content here.",
        )
        result = resp.apply_to_page(fake_page, FLAG_MESSAGE)
        assert result.snippet == FLAG_MESSAGE
        assert result.content == "Cleaned content here."

    @pytest.mark.ai
    def test_apply_to_page__preserves_url_and_title(
        self, fake_page: WebSearchResult
    ) -> None:
        resp = LLMGuardResponse(reasoning="OK", sanitized_content="sanitized")
        result = resp.apply_to_page(fake_page, FLAG_MESSAGE)
        assert result.url == fake_page.url
        assert result.title == fake_page.title


# ---------------------------------------------------------------------------
# JudgeAndSanitizeResponse tests
# ---------------------------------------------------------------------------


class TestJudgeAndSanitizeResponse:
    @pytest.mark.ai
    def test_apply_to_page__sets_content_when_sanitized(
        self, fake_page: WebSearchResult
    ) -> None:
        resp = JudgeAndSanitizeResponse(
            reasoning="Found health data.",
            needs_sanitization=True,
            sanitized_content="Redacted content.",
        )
        result = resp.apply_to_page(fake_page, FLAG_MESSAGE)
        assert result.snippet == FLAG_MESSAGE
        assert result.content == "Redacted content."

    @pytest.mark.ai
    def test_apply_to_page__raises_when_content_is_none(
        self, fake_page: WebSearchResult
    ) -> None:
        resp = JudgeAndSanitizeResponse(
            reasoning="No sensitive data.",
            needs_sanitization=False,
            sanitized_content=None,
        )
        with pytest.raises(ValueError, match="sanitized_content is None"):
            resp.apply_to_page(fake_page, FLAG_MESSAGE)


# ---------------------------------------------------------------------------
# LLMGuardJudge.__call__ dispatch tests
# ---------------------------------------------------------------------------


class TestLLMGuardJudgeDispatch:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__always_sanitize__calls_sanitize_page(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.ALWAYS_SANITIZE)
        llm_service = _mock_llm_service(
            {
                "reasoning": "No issues.",
                "sanitized_content": "Sanitized text.",
            }
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        result = await judge(page=fake_page, query=fake_query)

        assert result.content == "Sanitized text."
        assert result.snippet == FLAG_MESSAGE
        llm_service.complete_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__judge_only__not_flagged__returns_original(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.JUDGE_ONLY)
        llm_service = _mock_llm_service(
            {"reasoning": "Clean page.", "needs_sanitization": False}
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        result = await judge(page=fake_page, query=fake_query)

        assert result.content == fake_page.content
        assert result.snippet == fake_page.snippet

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__judge_only__flagged__replaces_content(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.JUDGE_ONLY)
        llm_service = _mock_llm_service(
            {"reasoning": "Health data found.", "needs_sanitization": True}
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        result = await judge(page=fake_page, query=fake_query)

        assert result.content == ""
        assert result.snippet == FLAG_MESSAGE

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__judge_and_sanitize__flagged__applies_sanitized_content(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.JUDGE_AND_SANITIZE)
        llm_service = _mock_llm_service(
            {
                "reasoning": "Health data found.",
                "needs_sanitization": True,
                "sanitized_content": "Redacted page content.",
            }
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        result = await judge(page=fake_page, query=fake_query)

        assert result.content == "Redacted page content."
        assert result.snippet == FLAG_MESSAGE

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__judge_and_sanitize__not_flagged__keeps_original(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.JUDGE_AND_SANITIZE)
        llm_service = _mock_llm_service(
            {
                "reasoning": "No sensitive data.",
                "needs_sanitization": False,
                "sanitized_content": None,
            }
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        result = await judge(page=fake_page, query=fake_query)

        assert result.content == fake_page.content
        assert result.snippet == fake_page.snippet

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__judge_then_sanitize__not_flagged__returns_original(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.JUDGE_THEN_SANITIZE)
        llm_service = _mock_llm_service(
            {"reasoning": "All clear.", "needs_sanitization": False}
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        result = await judge(page=fake_page, query=fake_query)

        assert result.content == fake_page.content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__judge_then_sanitize__flagged__runs_sanitize(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.JUDGE_THEN_SANITIZE)
        llm_service = Mock()

        judge_resp = Mock()
        judge_resp.choices = [
            Mock(
                message=Mock(
                    parsed={
                        "reasoning": "Sensitive data.",
                        "needs_sanitization": True,
                    }
                )
            )
        ]

        sanitize_resp = Mock()
        sanitize_resp.choices = [
            Mock(
                message=Mock(
                    parsed={
                        "reasoning": "Redacted.",
                        "sanitized_content": "Clean output.",
                    }
                )
            )
        ]

        llm_service.complete_async = AsyncMock(side_effect=[judge_resp, sanitize_resp])

        judge = LLMGuardJudge(config=config, llm_service=llm_service)
        result = await judge(page=fake_page, query=fake_query)

        assert result.content == "Clean output."
        assert result.snippet == FLAG_MESSAGE
        assert llm_service.complete_async.call_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__unknown_mode__raises_value_error(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.ALWAYS_SANITIZE)
        llm_service = Mock()
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        with patch.object(config.privacy_filter, "sanitize_mode", "invalid_mode"):
            with pytest.raises(ValueError, match="Unknown sanitize_mode"):
                await judge(page=fake_page, query=fake_query)


# ---------------------------------------------------------------------------
# LLMGuardJudge individual method tests
# ---------------------------------------------------------------------------


class TestLLMGuardJudgeMethods:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_sanitize_page__returns_sanitized_result(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config()
        llm_service = _mock_llm_service(
            {
                "reasoning": "Clean.",
                "sanitized_content": "Sanitized output.",
            }
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        result = await judge.sanitize_page(page=fake_page, query=fake_query)

        assert result.content == "Sanitized output."
        assert result.snippet == FLAG_MESSAGE

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_judge_only__returns_tuple(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config()
        llm_service = _mock_llm_service(
            {"reasoning": "No issues.", "needs_sanitization": False}
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        needs_san, returned_page = await judge.judge_only(
            page=fake_page, query=fake_query
        )

        assert needs_san is False
        assert returned_page is fake_page

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_judge_only__flagged__returns_true(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config()
        llm_service = _mock_llm_service(
            {"reasoning": "Health data.", "needs_sanitization": True}
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        needs_san, returned_page = await judge.judge_only(
            page=fake_page, query=fake_query
        )

        assert needs_san is True
        assert returned_page is fake_page

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_judge_and_sanitize__flagged__applies_content(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config()
        llm_service = _mock_llm_service(
            {
                "reasoning": "Found data.",
                "needs_sanitization": True,
                "sanitized_content": "Redacted.",
            }
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        needs_san, result_page = await judge.judge_and_sanitize(
            page=fake_page, query=fake_query
        )

        assert needs_san is True
        assert result_page.content == "Redacted."
        assert result_page.snippet == FLAG_MESSAGE

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_judge_and_sanitize__not_flagged__keeps_original(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config()
        llm_service = _mock_llm_service(
            {
                "reasoning": "Clean.",
                "needs_sanitization": False,
                "sanitized_content": None,
            }
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        needs_san, result_page = await judge.judge_and_sanitize(
            page=fake_page, query=fake_query
        )

        assert needs_san is False
        assert result_page.content == fake_page.content


# ---------------------------------------------------------------------------
# _complete error handling
# ---------------------------------------------------------------------------


class TestLLMGuardJudgeComplete:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_complete__raises_when_parsed_is_none(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config()
        llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(parsed=None))]
        llm_service.complete_async = AsyncMock(return_value=mock_resp)

        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        with pytest.raises(ValueError, match="no parsed response"):
            await judge.sanitize_page(page=fake_page, query=fake_query)


class TestLLMGuardJudgeUsage:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_always_sanitize__usage_recorded_on_debug_info(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.ALWAYS_SANITIZE)
        llm_service = _mock_llm_service(
            {"reasoning": "Clean.", "sanitized_content": "Sanitized."},
            usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            ),
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)
        debug_info = WebSearchDebugInfo(parameters={})

        await judge(page=fake_page, query=fake_query, debug_info=debug_info)

        assert len(debug_info.invocation_stats) == 1
        stat = debug_info.invocation_stats[0]
        assert stat.model_name == config.language_model.name
        assert stat.token_usage == LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=2, total_tokens=3
        )
        assert stat.source == "web_search_llm_guard_judge"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_judge_only__usage_recorded_on_debug_info(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.JUDGE_ONLY)
        llm_service = _mock_llm_service(
            {"reasoning": "Clean.", "needs_sanitization": False},
            usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)
        debug_info = WebSearchDebugInfo(parameters={})

        await judge(page=fake_page, query=fake_query, debug_info=debug_info)

        assert len(debug_info.invocation_stats) == 1
        stat = debug_info.invocation_stats[0]
        assert stat.model_name == config.language_model.name
        assert stat.token_usage == LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=1, total_tokens=2
        )
        assert stat.source == "web_search_llm_guard_judge"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_judge_then_sanitize__flagged__sums_usage_from_both_calls(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(sanitize_mode=SanitizeMode.JUDGE_THEN_SANITIZE)
        judge = LLMGuardJudge(config=config, llm_service=Mock())

        judge_response = Mock()
        judge_response.choices = [
            Mock(
                message=Mock(
                    parsed={"reasoning": "Flagged.", "needs_sanitization": True}
                )
            )
        ]
        judge_response.usage = LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=1, total_tokens=2
        )

        sanitize_response = Mock()
        sanitize_response.choices = [
            Mock(
                message=Mock(
                    parsed={
                        "reasoning": "Sanitized.",
                        "sanitized_content": "Redacted.",
                    }
                )
            )
        ]
        sanitize_response.usage = LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )

        judge._llm_service.complete_async = AsyncMock(
            side_effect=[judge_response, sanitize_response]
        )
        debug_info = WebSearchDebugInfo(parameters={})

        result = await judge(page=fake_page, query=fake_query, debug_info=debug_info)

        assert result.content == "Redacted."
        assert len(debug_info.invocation_stats) == 2
        judge_stat, sanitize_stat = debug_info.invocation_stats
        assert judge_stat.model_name == config.language_model.name
        assert judge_stat.token_usage == LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=1, total_tokens=2
        )
        assert judge_stat.source == "web_search_llm_guard_judge"
        assert sanitize_stat.model_name == config.language_model.name
        assert sanitize_stat.token_usage == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )
        assert sanitize_stat.source == "web_search_llm_guard_judge"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_judge_then_sanitize__not_flagged__usage_from_judge_call_only(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(sanitize_mode=SanitizeMode.JUDGE_THEN_SANITIZE)
        llm_service = _mock_llm_service(
            {"reasoning": "Clean.", "needs_sanitization": False},
            usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)
        debug_info = WebSearchDebugInfo(parameters={})

        await judge(page=fake_page, query=fake_query, debug_info=debug_info)

        assert len(debug_info.invocation_stats) == 1
        stat = debug_info.invocation_stats[0]
        assert stat.model_name == config.language_model.name
        assert stat.token_usage == LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=1, total_tokens=2
        )
        assert stat.source == "web_search_llm_guard_judge"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_no_debug_info__does_not_raise(
        self, fake_page: WebSearchResult, fake_query: str
    ) -> None:
        config = _make_config(SanitizeMode.ALWAYS_SANITIZE)
        llm_service = _mock_llm_service(
            {"reasoning": "Clean.", "sanitized_content": "Sanitized."}
        )
        judge = LLMGuardJudge(config=config, llm_service=llm_service)

        result = await judge(page=fake_page, query=fake_query)

        assert result.content == "Sanitized."
