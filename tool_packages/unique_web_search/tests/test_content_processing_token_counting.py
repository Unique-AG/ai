from unittest.mock import AsyncMock, Mock

import pytest

from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcess,
    LLMProcessorConfig,
)
from unique_web_search.services.content_processing.processing_strategies.truncate import (
    Truncate,
    TruncateConfig,
)
from unique_web_search.services.search_engine.schema import WebSearchResult


def _simple_encoder(text: str) -> list[int]:
    return list(range(len(text.split())))


def _simple_decoder(tokens: list[int]) -> str:
    return " ".join(["word"] * len(tokens))


@pytest.mark.asyncio
async def test_summarize_page_uses_encoder():
    config = LLMProcessorConfig(enabled=True, min_tokens=0)
    mock_llm_service = Mock()
    mock_response = Mock()
    mock_response.choices = [
        Mock(
            message=Mock(
                parsed={
                    "snippet": "Summarized snippet",
                    "summary": "Summarized content",
                }
            )
        )
    ]
    mock_llm_service.complete_async = AsyncMock(return_value=mock_response)

    processor = LLMProcess(
        config=config,
        llm_service=mock_llm_service,
        encoder=_simple_encoder,
        decoder=_simple_decoder,
    )
    page = WebSearchResult(
        url="http://test.com",
        title="Test",
        snippet="s",
        content="Test content " * 100,
    )

    result = await processor(page=page, query="test query")

    assert result.content == "Summarized content"
    assert result.snippet == "Summarized snippet"
    mock_llm_service.complete_async.assert_called_once()


def test_truncate_page():
    long_content = (
        "This is a test sentence with multiple words that count as tokens. " * 50
    )
    config = TruncateConfig(max_tokens=50)
    truncate = Truncate(
        encoder=_simple_encoder,
        decoder=_simple_decoder,
        config=config,
    )
    page = WebSearchResult(
        url="http://test.com",
        title="Test",
        snippet="s",
        content=long_content,
    )
    original_length = len(page.content)

    import asyncio

    result = asyncio.run(truncate(page=page, query="test"))

    assert len(result.content) < original_length
    assert len(result.content) > 0
