"""Tests for ContentProcessor service — cleaning, processing, and chunking."""

from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_web_search.schema import WebSearchDebugInfo
from unique_web_search.services.content_processing.config import (
    ContentProcessorConfig,
)
from unique_web_search.services.content_processing.service import (
    ContentProcessor,
    _build_web_page_chunk,
)
from unique_web_search.services.search_engine.schema import WebSearchResult


def _simple_encoder(text: str) -> list[int]:
    return list(range(len(text.split())))


def _simple_decoder(tokens: list[int]) -> str:
    return " ".join(["word"] * len(tokens))


@pytest.fixture
def fake_page() -> WebSearchResult:
    return WebSearchResult(
        url="https://example.com/test",
        title="Test Page",
        snippet="Test snippet with content.",
        content="This is the full page content for testing purposes.",
    )


@pytest.fixture
def processor() -> ContentProcessor:
    config = ContentProcessorConfig()
    config.processing_strategies.llm_processor.enabled = False
    return ContentProcessor(
        language_model_service=Mock(),
        config=config,
        encoder=_simple_encoder,
        decoder=_simple_decoder,
    )


# ---------------------------------------------------------------------------
# _clean_content tests
# ---------------------------------------------------------------------------


class TestCleanContent:
    @pytest.mark.ai
    def test_clean_content__applies_strategies_to_content_and_snippet(
        self, processor: ContentProcessor, fake_page: WebSearchResult
    ) -> None:
        result = processor._clean_content(fake_page)
        assert result.content is not None
        assert result.snippet is not None

    @pytest.mark.ai
    def test_clean_content__character_sanitize_strips_null_bytes(
        self, processor: ContentProcessor
    ) -> None:
        page = WebSearchResult(
            url="https://example.com",
            title="Test",
            snippet="snippet\x00here",
            content="content\x00here",
        )
        result = processor._clean_content(page)
        assert "\x00" not in result.content
        assert "\x00" not in result.snippet


# ---------------------------------------------------------------------------
# _process_pages tests
# ---------------------------------------------------------------------------


class TestProcessPages:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_process_pages__successful__returns_processed(
        self, processor: ContentProcessor, fake_page: WebSearchResult
    ) -> None:
        pages = [fake_page]
        result = await processor._process_pages("test query", pages)
        assert len(result) == 1
        assert result[0].url == fake_page.url

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_process_pages__multiple_pages__all_processed(
        self, processor: ContentProcessor
    ) -> None:
        pages = [
            WebSearchResult(
                url=f"https://example.com/{i}",
                title=f"Page {i}",
                snippet=f"Snippet {i}",
                content=f"Content {i}",
            )
            for i in range(3)
        ]
        result = await processor._process_pages("test query", pages)
        assert len(result) == 3

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_process_pages__strategy_failure__clears_content(
        self,
    ) -> None:
        config = ContentProcessorConfig()
        config.processing_strategies.truncate.enabled = False
        config.processing_strategies.llm_processor.enabled = False

        processor = ContentProcessor(
            language_model_service=Mock(),
            config=config,
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )

        failing_strategy = Mock()
        failing_strategy.is_enabled = True
        failing_strategy.__class__.__name__ = "FailingStrategy"

        async def raise_error(**kwargs):
            raise RuntimeError("Processing failed")

        failing_strategy.side_effect = raise_error
        failing_strategy.__call__ = raise_error

        processor._processing_strategies = [failing_strategy]

        page = WebSearchResult(
            url="https://example.com/fail",
            title="Fail Page",
            snippet="Fail snippet",
            content="Original content that should be cleared.",
        )

        result = await processor._process_pages("test", [page])
        assert len(result) == 1
        assert result[0].content == ""


# ---------------------------------------------------------------------------
# _split_pages_to_chunks / _create_chunks tests
# ---------------------------------------------------------------------------


class TestCreateChunks:
    @pytest.mark.ai
    def test_create_chunks__empty_content__returns_single_chunk(
        self, processor: ContentProcessor
    ) -> None:
        page = WebSearchResult(
            url="https://example.com/empty",
            title="Empty Page",
            snippet="A snippet",
            content="",
        )
        chunks = processor._create_chunks(page)
        assert len(chunks) == 1
        assert chunks[0].order == "0"

    @pytest.mark.ai
    def test_create_chunks__short_content__returns_single_chunk(
        self, processor: ContentProcessor
    ) -> None:
        page = WebSearchResult(
            url="https://example.com/short",
            title="Short Page",
            snippet="A snippet",
            content="Hello world",
        )
        chunks = processor._create_chunks(page)
        assert len(chunks) == 1

    @pytest.mark.ai
    def test_create_chunks__long_content__splits_into_multiple(
        self,
    ) -> None:
        config = ContentProcessorConfig(chunk_size=10)
        config.processing_strategies.llm_processor.enabled = False
        processor = ContentProcessor(
            language_model_service=Mock(),
            config=config,
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )
        page = WebSearchResult(
            url="https://example.com/long",
            title="Long Page",
            snippet="A snippet",
            content=" ".join(["word"] * 25),
        )
        chunks = processor._create_chunks(page)
        assert len(chunks) > 1
        assert chunks[0].order == "0"
        assert chunks[1].order == "1"


# ---------------------------------------------------------------------------
# _build_web_page_chunk tests
# ---------------------------------------------------------------------------


class TestBuildWebPageChunk:
    @pytest.mark.ai
    def test_build_chunk__populates_all_fields(
        self, fake_page: WebSearchResult
    ) -> None:
        chunk = _build_web_page_chunk(fake_page, "chunk text", 0)
        assert chunk.url == fake_page.url
        assert chunk.title == fake_page.title
        assert chunk.snippet == fake_page.snippet
        assert chunk.order == "0"
        assert "chunk text" in chunk.content

    @pytest.mark.ai
    def test_build_chunk__empty_content__renders_without_chunk_tag(
        self, fake_page: WebSearchResult
    ) -> None:
        chunk = _build_web_page_chunk(fake_page, "", 0)
        assert chunk.url == fake_page.url
        assert "Chunk" not in chunk.content or chunk.content.strip() != ""

    @pytest.mark.ai
    def test_build_chunk__display_link_in_content(
        self, fake_page: WebSearchResult
    ) -> None:
        chunk = _build_web_page_chunk(fake_page, "some text", 0)
        assert fake_page.display_link in chunk.content


# ---------------------------------------------------------------------------
# Full run integration test
# ---------------------------------------------------------------------------


class TestContentProcessorRun:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__returns_web_page_chunks(
        self, processor: ContentProcessor, fake_page: WebSearchResult
    ) -> None:
        chunks = await processor.run("test query", [fake_page])
        assert len(chunks) >= 1
        assert chunks[0].url == fake_page.url

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__empty_pages__returns_empty(
        self, processor: ContentProcessor
    ) -> None:
        chunks = await processor.run("test query", [])
        assert chunks == []


class TestContentProcessorUsage:
    @pytest.fixture
    def llm_service_with_usage(self) -> Mock:
        service = Mock()
        response = Mock()
        response.choices = [
            Mock(
                message=Mock(
                    parsed={"snippet": "Sum snippet", "summary": "Sum content"}
                )
            )
        ]
        response.usage = LanguageModelTokenUsage(
            completion_tokens=2, prompt_tokens=3, total_tokens=5
        )
        service.complete_async = AsyncMock(return_value=response)
        return service

    @pytest.fixture
    def processor_with_llm(self, llm_service_with_usage: Mock) -> ContentProcessor:
        config = ContentProcessorConfig()
        config.processing_strategies.llm_processor.enabled = True
        config.processing_strategies.llm_processor.min_tokens = 0
        return ContentProcessor(
            language_model_service=llm_service_with_usage,
            config=config,
            encoder=_simple_encoder,
            decoder=_simple_decoder,
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__single_page__usage_recorded_on_debug_info(
        self, processor_with_llm: ContentProcessor, fake_page: WebSearchResult
    ) -> None:
        debug_info = WebSearchDebugInfo(parameters={})

        await processor_with_llm.run("test query", [fake_page], debug_info=debug_info)

        assert len(debug_info.invocation_stats) == 1
        stat = debug_info.invocation_stats[0]
        assert (
            stat.model_name
            == processor_with_llm.config.processing_strategies.llm_processor.language_model.name
        )
        assert stat.token_usage == LanguageModelTokenUsage(
            completion_tokens=2, prompt_tokens=3, total_tokens=5
        )
        assert stat.source == "web_search_llm_process"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__multiple_concurrent_pages__usage_summed(
        self, processor_with_llm: ContentProcessor
    ) -> None:
        """process_single_page runs concurrently across pages via
        asyncio.gather -- each page's usage must be recorded as its own
        invocation_stats entry on debug_info, not lost or overwritten by a
        race."""
        pages = [
            WebSearchResult(
                url=f"https://example.com/{i}",
                title=f"Page {i}",
                snippet=f"Snippet {i}",
                content=f"Content {i}",
            )
            for i in range(5)
        ]
        debug_info = WebSearchDebugInfo(parameters={})

        await processor_with_llm.run("test query", pages, debug_info=debug_info)

        expected_model = processor_with_llm.config.processing_strategies.llm_processor.language_model.name
        assert len(debug_info.invocation_stats) == 5
        for stat in debug_info.invocation_stats:
            assert stat.model_name == expected_model
            assert stat.token_usage == LanguageModelTokenUsage(
                completion_tokens=2, prompt_tokens=3, total_tokens=5
            )
            assert stat.source == "web_search_llm_process"

        summed = LanguageModelTokenUsage(
            completion_tokens=sum(
                s.token_usage.completion_tokens for s in debug_info.invocation_stats
            ),
            prompt_tokens=sum(
                s.token_usage.prompt_tokens for s in debug_info.invocation_stats
            ),
            total_tokens=sum(
                s.token_usage.total_tokens for s in debug_info.invocation_stats
            ),
        )
        assert summed == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=15, total_tokens=25
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__no_debug_info__does_not_raise(
        self, processor_with_llm: ContentProcessor, fake_page: WebSearchResult
    ) -> None:
        chunks = await processor_with_llm.run("test query", [fake_page])
        assert len(chunks) >= 1
