from unittest.mock import patch

import pytest

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.content.utils import (
    _apply_ingestion_upload_url_override,
    count_tokens,
    map_content,
    map_content_chunk,
    merge_content_chunks,
    pick_content_chunks_for_token_window,
    sort_content_chunks,
)


class TestContentChunkUtils:
    def test_sort_content_chunks(self):
        chunks = [
            ContentChunk(
                id="1",
                order=2,
                text="<|content|>Second<|/content|>",
                start_page=2,
                end_page=2,
            ),
            ContentChunk(
                id="1",
                order=1,
                text="<|content|>First<|/content|>",
                start_page=1,
                end_page=1,
            ),
            ContentChunk(
                id="2",
                order=1,
                text="<|content|>Another<|/content|>",
                start_page=1,
                end_page=1,
            ),
        ]
        sorted_chunks = sort_content_chunks(chunks)

        assert len(sorted_chunks) == 3
        assert sorted_chunks[0].order == 1 and "First" in sorted_chunks[0].text
        assert sorted_chunks[1].order == 2 and "Second" in sorted_chunks[1].text
        assert sorted_chunks[2].order == 1 and "Another" in sorted_chunks[2].text
        assert "text part 1" in sorted_chunks[0].text
        assert "text part 2" in sorted_chunks[1].text

    def test_merge_content_chunks(self):
        chunks = [
            ContentChunk(
                id="1",
                order=2,
                text="<|content|>Second<|/content|>",
                start_page=2,
                end_page=2,
            ),
            ContentChunk(
                id="1",
                order=1,
                text="<|content|>First<|/content|>",
                start_page=1,
                end_page=1,
            ),
            ContentChunk(
                id="2",
                order=1,
                text="<|content|>Another<|/content|>",
                start_page=1,
                end_page=1,
            ),
        ]
        merged_chunks = merge_content_chunks(chunks)

        assert len(merged_chunks) == 2
        assert merged_chunks[0].id == "1"
        assert merged_chunks[0].text == "<|content|>First<|/content|>\n"
        assert merged_chunks[0].start_page == 1 and merged_chunks[0].end_page == 2
        assert merged_chunks[1].id == "2"
        assert merged_chunks[1].text == "<|content|>Another<|/content|>"

    def test_pick_content_chunks_for_token_window(self):
        chunks = [
            ContentChunk(id="1", text="Short text", order=1),
            ContentChunk(id="2", text="A bit longer text", order=2),
            ContentChunk(id="3", text="This is the longest text in the list", order=3),
        ]

        # token limit should pick the first two chunks
        picked_chunks = pick_content_chunks_for_token_window(chunks, token_limit=10)

        assert len(picked_chunks) == 2
        assert picked_chunks[0].id == "1"
        assert picked_chunks[1].id == "2"

    @pytest.mark.ai
    def test_pick_content_chunks_for_token_window_with_model(self):
        from unique_toolkit.language_model.infos import (
            LanguageModelInfo,
            LanguageModelName,
        )

        chunks = [
            ContentChunk(id="1", text="你好世界", order=1),
            ContentChunk(id="2", text="这是一个测试", order=2),
            ContentChunk(id="3", text="非常长的文本内容 " * 50, order=3),
        ]

        model_info = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)

        picked_chunks = pick_content_chunks_for_token_window(
            chunks, token_limit=50, model_info=model_info
        )

        assert len(picked_chunks) < len(chunks)
        assert len(picked_chunks) > 0

    def test_count_tokens(self):
        text = "This is a sample text to count tokens."
        token_count = count_tokens(text)

        assert token_count > 0
        assert isinstance(token_count, int)

    def test_map_content_chunk(self):
        content_chunk_dict = {
            "id": "chunk_123",
            "text": "Sample text",
            "startPage": 1,
            "endPage": 2,
            "order": 1,
        }
        metadata = {"key": "file.pdf", "mime_type": "application/pdf"}

        result = map_content_chunk("cont_456", "file.pdf", content_chunk_dict, metadata)

        assert result.id == "cont_456"
        assert result.chunk_id == "chunk_123"
        assert result.text == "Sample text"
        assert result.metadata is not None

    def test_map_content(self):
        content_dict = {
            "id": "cont_123",
            "key": "document.pdf",
            "title": "Test Document",
            "url": "https://example.com/doc.pdf",
            "chunks": [
                {
                    "id": "chunk_1",
                    "text": "First chunk",
                    "startPage": 1,
                    "endPage": 1,
                    "order": 1,
                }
            ],
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }

        result = map_content(content_dict)

        assert result.id == "cont_123"
        assert result.key == "document.pdf"
        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == "chunk_1"


class TestApplyIngestionUploadUrlOverride:
    def test_returns_original_url_when_env_unset(self):
        write_url = "https://gateway.example.com/ingestion/upload?key=abc123"
        assert _apply_ingestion_upload_url_override(write_url) == write_url

    def test_returns_original_url_when_env_empty(self):
        write_url = "https://gateway.example.com/ingestion/upload?key=abc123"
        with patch(
            "unique_toolkit.content.utils._ingestion_upload_api_url_internal", None
        ):
            assert _apply_ingestion_upload_url_override(write_url) == write_url

    def test_replaces_base_preserves_query_when_env_set(self):
        write_url = "https://gateway.example.com/ingestion/upload?key=encrypted%3Dvalue"
        internal_base = "https://node-ingestion.namespace.svc.cluster.local/upload"
        with patch(
            "unique_toolkit.content.utils._ingestion_upload_api_url_internal",
            internal_base,
        ):
            result = _apply_ingestion_upload_url_override(write_url)
        assert (
            result
            == "https://node-ingestion.namespace.svc.cluster.local/upload?key=encrypted%3Dvalue"
        )

    def test_replaces_base_no_double_question_mark_when_no_query(self):
        write_url = "https://gateway.example.com/ingestion/upload"
        internal_base = "http://ingestion-internal/upload"
        with patch(
            "unique_toolkit.content.utils._ingestion_upload_api_url_internal",
            internal_base,
        ):
            result = _apply_ingestion_upload_url_override(write_url)
        assert result == "http://ingestion-internal/upload"

    def test_strips_trailing_slash_from_custom_base(self):
        write_url = "https://gateway.example.com/upload?key=xyz"
        internal_base = "https://internal/upload/"
        with patch(
            "unique_toolkit.content.utils._ingestion_upload_api_url_internal",
            internal_base,
        ):
            result = _apply_ingestion_upload_url_override(write_url)
        assert result == "https://internal/upload?key=xyz"
