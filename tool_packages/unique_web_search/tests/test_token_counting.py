from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

from unique_web_search.services.content_processing import WebPageChunk
from unique_web_search.utils import reduce_sources_to_token_limit


def test_reduce_sources_with_model():
    chunks = [
        WebPageChunk(
            url="http://test.com",
            display_link="test.com",
            title="Test",
            snippet="s",
            content="Short content " * 10,
            order="1",
        ),
        WebPageChunk(
            url="http://test2.com",
            display_link="test2.com",
            title="Test 2",
            snippet="s",
            content="Very long content " * 100,
            order="2",
        ),
    ]
    language_model = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_0513
    )

    result = reduce_sources_to_token_limit(
        web_page_chunks=chunks,
        language_model_max_input_tokens=None,
        percentage_of_input_tokens_for_sources=0.4,
        limit_token_sources=100,
        language_model=language_model,
        chat_history_token_length=10,
    )

    assert len(result) > 0
