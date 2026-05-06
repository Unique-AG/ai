"""Tests for LLMProcess dispatch logic — sanitize modes, keyword redact, guard judge."""

from unittest.mock import AsyncMock, Mock

import pytest

from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcess,
    LLMProcessorConfig,
    PrivacyFilterConfig,
)
from unique_web_search.services.content_processing.processing_strategies.settings import (
    SanitizeMode,
)
from unique_web_search.services.search_engine.schema import WebSearchResult


def _simple_encoder(text: str) -> list[int]:
    return list(range(len(text.split())))


def _simple_decoder(tokens: list[int]) -> str:
    return " ".join(["word"] * len(tokens))


@pytest.fixture
def fake_page() -> WebSearchResult:
    return WebSearchResult(
        url="https://example.com/long",
        title="Long Page",
        snippet="A snippet",
        content="word " * 6000,
    )


@pytest.fixture
def short_page() -> WebSearchResult:
    return WebSearchResult(
        url="https://example.com/short",
        title="Short Page",
        snippet="A snippet",
        content="short content",
    )


# ---------------------------------------------------------------------------
# should_run tests
# ---------------------------------------------------------------------------


class TestShouldRun:
    @pytest.mark.ai
    def test_should_run__sanitize_enabled__returns_true_regardless_of_length(
        self,
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=99999,
            privacy_filter=PrivacyFilterConfig(sanitize=True),
        )
        assert config.should_run(_simple_encoder, "short") is True

    @pytest.mark.ai
    def test_should_run__sanitize_disabled__short_content__returns_false(
        self,
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=100,
            privacy_filter=PrivacyFilterConfig(sanitize=False),
        )
        assert config.should_run(_simple_encoder, "short") is False

    @pytest.mark.ai
    def test_should_run__sanitize_disabled__long_content__returns_true(
        self,
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=5,
            privacy_filter=PrivacyFilterConfig(sanitize=False),
        )
        assert config.should_run(_simple_encoder, "a b c d e f g") is True


# ---------------------------------------------------------------------------
# LLMProcess.__call__ dispatch
# ---------------------------------------------------------------------------


class TestLLMProcessDispatch:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__disabled__returns_page_unchanged(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(enabled=False)
        processor = LLMProcess(
            config=config,
            llm_service=Mock(),
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        result = await processor(page=fake_page, query="test")
        assert result is fake_page

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__missing_query__raises_value_error(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(enabled=True, min_tokens=0)
        processor = LLMProcess(
            config=config,
            llm_service=Mock(),
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        with pytest.raises(ValueError, match="Query is required"):
            await processor(page=fake_page, query=None)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__content_below_threshold__skips_processing(
        self, short_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=99999,
            privacy_filter=PrivacyFilterConfig(sanitize=False),
        )
        processor = LLMProcess(
            config=config,
            llm_service=Mock(),
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        result = await processor(page=short_page, query="test")
        assert result is short_page

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__sanitize_off__dispatches_to_summarize(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=0,
            privacy_filter=PrivacyFilterConfig(sanitize=False),
        )
        mock_llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [
            Mock(
                message=Mock(
                    parsed={"snippet": "Sum snippet", "summary": "Sum content"}
                )
            )
        ]
        mock_llm_service.complete_async = AsyncMock(return_value=mock_resp)

        processor = LLMProcess(
            config=config,
            llm_service=mock_llm_service,
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        result = await processor(page=fake_page, query="test query")
        assert result.content == "Sum content"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__keyword_redact_mode__dispatches_to_keyword_redact(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=0,
            privacy_filter=PrivacyFilterConfig(
                sanitize=True,
                sanitize_mode=SanitizeMode.KEYWORD_REDACT,
            ),
        )
        mock_llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(parsed={"sensitive_keywords": []}))]
        mock_llm_service.complete_async = AsyncMock(return_value=mock_resp)

        processor = LLMProcess(
            config=config,
            llm_service=mock_llm_service,
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        result = await processor(page=fake_page, query="test query")
        assert result.url == fake_page.url
        mock_llm_service.complete_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__always_sanitize_mode__dispatches_to_guard_judge(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=0,
            privacy_filter=PrivacyFilterConfig(
                sanitize=True,
                sanitize_mode=SanitizeMode.ALWAYS_SANITIZE,
            ),
        )
        mock_llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [
            Mock(
                message=Mock(
                    parsed={
                        "reasoning": "OK.",
                        "sanitized_content": "Guard output.",
                    }
                )
            )
        ]
        mock_llm_service.complete_async = AsyncMock(return_value=mock_resp)

        processor = LLMProcess(
            config=config,
            llm_service=mock_llm_service,
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        result = await processor(page=fake_page, query="test query")
        assert result.content == "Guard output."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__judge_only_mode__dispatches_to_guard_judge(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=0,
            privacy_filter=PrivacyFilterConfig(
                sanitize=True,
                sanitize_mode=SanitizeMode.JUDGE_ONLY,
            ),
        )
        mock_llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [
            Mock(
                message=Mock(
                    parsed={"reasoning": "Clean.", "needs_sanitization": False}
                )
            )
        ]
        mock_llm_service.complete_async = AsyncMock(return_value=mock_resp)

        processor = LLMProcess(
            config=config,
            llm_service=mock_llm_service,
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        result = await processor(page=fake_page, query="test query")
        assert result.url == fake_page.url

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__judge_then_sanitize_mode__dispatches_to_guard_judge(
        self, fake_page: WebSearchResult
    ) -> None:
        config = LLMProcessorConfig(
            enabled=True,
            min_tokens=0,
            privacy_filter=PrivacyFilterConfig(
                sanitize=True,
                sanitize_mode=SanitizeMode.JUDGE_THEN_SANITIZE,
            ),
        )
        mock_llm_service = Mock()
        mock_resp = Mock()
        mock_resp.choices = [
            Mock(
                message=Mock(
                    parsed={"reasoning": "Clean.", "needs_sanitization": False}
                )
            )
        ]
        mock_llm_service.complete_async = AsyncMock(return_value=mock_resp)

        processor = LLMProcess(
            config=config,
            llm_service=mock_llm_service,
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        result = await processor(page=fake_page, query="test query")
        assert result.url == fake_page.url
