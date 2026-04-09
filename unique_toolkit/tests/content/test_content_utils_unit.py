from unittest.mock import patch

import pytest

from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.content.utils import (
    _apply_ingestion_upload_url_override,
    content_chunk_to_reference,
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

    @pytest.mark.ai
    def test_map_content__ingestion_config_and_applied_ingestion_config__mapped_when_present(
        self,
    ):
        """
        Purpose: Verifies that map_content correctly maps ingestionConfig and
        appliedIngestionConfig from the source dict to Content model fields.
        Why this matters: Missing these fields would cause ingestion configuration
        to be silently dropped, breaking features that rely on knowing how content
        was ingested.
        Setup summary: Provide a content dict with both ingestionConfig and
        appliedIngestionConfig; assert both are present on the result.
        """
        content_dict = {
            "id": "cont_abc",
            "key": "file.pdf",
            "title": "File",
            "url": "https://example.com/file.pdf",
            "chunks": [],
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "ingestionConfig": {"chunkSize": 512, "overlap": 64},
            "appliedIngestionConfig": {"chunkSize": 256, "overlap": 32},
        }

        result = map_content(content_dict)

        assert result.ingestion_config == {"chunkSize": 512, "overlap": 64}
        assert result.applied_ingestion_config == {"chunkSize": 256, "overlap": 32}

    @pytest.mark.ai
    def test_map_content__ingestion_config_and_applied_ingestion_config__none_when_absent(
        self,
    ):
        """
        Purpose: Verifies that map_content defaults ingestion_config and
        applied_ingestion_config to None when absent from the source dict.
        Why this matters: The fields are optional; code that checks for None must
        not break when the API omits them.
        Setup summary: Provide a content dict without ingestionConfig or
        appliedIngestionConfig; assert both fields on the result are None.
        """
        content_dict = {
            "id": "cont_xyz",
            "key": "doc.pdf",
            "title": "Doc",
            "url": "https://example.com/doc.pdf",
            "chunks": [],
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }

        result = map_content(content_dict)

        assert result.ingestion_config is None
        assert result.applied_ingestion_config is None


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


class TestContentChunkToReference:
    def test_basic_reference_with_pages(self):
        chunk = ContentChunk(
            id="cont_123",
            chunk_id="chunk_abc",
            title="Report.pdf",
            text="some text",
            order=1,
            start_page=3,
            end_page=5,
        )
        ref = chunk.to_reference(sequence_number=1)

        assert isinstance(ref, ContentReference)
        assert ref.id == "cont_123"
        assert ref.message_id == ""
        assert ref.name == "Report.pdf : 3,4,5"
        assert ref.sequence_number == 1
        assert ref.source_id == "cont_123_chunk_abc"
        assert ref.source == "node-ingestion-chunks"
        assert ref.url == "unique://content/cont_123"

    def test_none_pages_do_not_crash(self):
        chunk = ContentChunk(
            id="cont_456",
            chunk_id="chunk_def",
            title="NoPagesDoc.pdf",
            text="text",
            order=1,
            start_page=None,
            end_page=None,
        )
        ref = chunk.to_reference(sequence_number=2)

        assert ref.name == "NoPagesDoc.pdf"
        assert ref.url == "unique://content/cont_456"

    def test_none_start_page_with_valid_end_page(self):
        chunk = ContentChunk(
            id="cont_789",
            chunk_id="chunk_ghi",
            title="Partial.pdf",
            text="text",
            order=1,
            start_page=None,
            end_page=5,
        )
        ref = chunk.to_reference(sequence_number=1)

        assert ref.name == "Partial.pdf"

    def test_valid_start_page_with_none_end_page(self):
        chunk = ContentChunk(
            id="cont_aaa",
            chunk_id="chunk_bbb",
            title="HalfPage.pdf",
            text="text",
            order=1,
            start_page=3,
            end_page=None,
        )
        ref = chunk.to_reference(sequence_number=1)

        assert ref.name == "HalfPage.pdf : 3"

    def test_url_uses_chunk_url_when_not_internally_stored(self):
        chunk = ContentChunk(
            id="cont_ext",
            chunk_id="chunk_ext",
            title="Web Page",
            text="text",
            order=1,
            url="https://example.com/page",
            internally_stored_at=None,
        )
        ref = chunk.to_reference(sequence_number=1)

        assert ref.url == "https://example.com/page"

    def test_url_falls_back_to_unique_when_internally_stored(self):
        from datetime import datetime

        chunk = ContentChunk(
            id="cont_int",
            chunk_id="chunk_int",
            title="Stored Doc",
            text="text",
            order=1,
            url="https://example.com/stored",
            internally_stored_at=datetime(2024, 7, 22, 11, 51, 40),
        )
        ref = chunk.to_reference(sequence_number=1)

        assert ref.url == "unique://content/cont_int"

    def test_url_falls_back_when_no_url(self):
        chunk = ContentChunk(
            id="cont_no_url",
            chunk_id="chunk_no",
            title="No URL",
            text="text",
            order=1,
            url=None,
        )
        ref = chunk.to_reference(sequence_number=1)

        assert ref.url == "unique://content/cont_no_url"

    def test_source_id_without_chunk_id(self):
        chunk = ContentChunk(
            id="cont_only",
            title="Doc",
            text="text",
            order=1,
        )
        ref = chunk.to_reference(sequence_number=1)

        assert ref.source_id == "cont_only"

    def test_original_index_passed_through(self):
        chunk = ContentChunk(
            id="cont_idx",
            chunk_id="chunk_idx",
            title="Doc",
            text="text",
            order=1,
        )
        ref = chunk.to_reference(sequence_number=3, original_index=[1, 4])

        assert ref.original_index == [1, 4]
        assert ref.sequence_number == 3

    def test_falls_back_to_key_when_no_title(self):
        chunk = ContentChunk(
            id="cont_key",
            chunk_id="chunk_key",
            key="document.pdf",
            text="text",
            order=1,
            start_page=1,
            end_page=1,
        )
        ref = chunk.to_reference(sequence_number=1)

        assert ref.name == "document.pdf : 1"

    def test_sets_message_id_when_provided(self):
        chunk = ContentChunk(
            id="cont_msg",
            chunk_id="chunk_msg",
            title="Doc",
            text="text",
            order=1,
        )
        ref = chunk.to_reference(sequence_number=1, message_id="msg_abc")

        assert ref.id == "cont_msg"
        assert ref.message_id == "msg_abc"

    def test_falls_back_to_content_id_when_no_title_or_key(self):
        chunk = ContentChunk(
            id="cont_noname",
            chunk_id="chunk_x",
            text="text",
            order=1,
            start_page=2,
            end_page=2,
        )
        ref = chunk.to_reference(sequence_number=1)

        assert ref.name == "Content cont_noname : 2"

    def test_to_reference_matches_content_chunk_to_reference(self):
        chunk = ContentChunk(
            id="cont_delegate",
            chunk_id="chunk_del",
            title="T",
            text="t",
            order=1,
        )
        via_fn = content_chunk_to_reference(
            chunk, sequence_number=2, original_index=[3], message_id="m1"
        )
        via_method = chunk.to_reference(
            sequence_number=2, original_index=[3], message_id="m1"
        )

        assert via_method.model_dump() == via_fn.model_dump()
