import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

from unique_web_search.services.content_processing.config import ContentProcessorConfig
from unique_web_search.services.content_processing.service import ContentProcessor
from unique_web_search.services.search_engine.schema import WebSearchResult


@pytest.mark.asyncio
async def test_summarize_page_uses_encoder():
    config = ContentProcessorConfig(
        language_model=LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0513
        )
    )
    processor = ContentProcessor(
        event=MagicMock(), config=config, language_model=config.language_model
    )
    page = WebSearchResult(
        url="http://test.com",
        display_link="test.com",
        title="Test",
        snippet="s",
        content="Test content " * 100,
    )

    with patch(
        "unique_web_search.services.content_processing.service.get_async_openai_client"
    ) as mock_client:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Summarized"))]
        mock_client.return_value.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await processor._summarize_page(page, "test query")
        assert result.content == "Summarized"


def test_truncate_page():
    long_content = (
        "This is a test sentence with multiple words that count as tokens. " * 50
    )
    config = ContentProcessorConfig(
        language_model=LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0513
        ),
        max_tokens=50,
    )
    processor = ContentProcessor(
        event=MagicMock(), config=config, language_model=config.language_model
    )
    page = WebSearchResult(
        url="http://test.com",
        display_link="test.com",
        title="Test",
        snippet="s",
        content=long_content,
    )
    original_length = len(page.content)

    result = asyncio.run(processor._truncate_page(page))

    assert len(result.content) < original_length
    assert len(result.content) > 0
