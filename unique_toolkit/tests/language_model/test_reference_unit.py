from datetime import datetime

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.reference import _find_references


def _chunk(
    id: str = "cont_1",
    chunk_id: str | None = "chunk_1",
    title: str | None = "Doc.pdf",
    key: str | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
    url: str | None = None,
    internally_stored_at: datetime | None = None,
) -> ContentChunk:
    return ContentChunk(
        id=id,
        chunk_id=chunk_id,
        title=title,
        key=key,
        text="chunk text",
        order=1,
        start_page=start_page,
        end_page=end_page,
        url=url,
        internally_stored_at=internally_stored_at,
    )


class TestFindReferences:
    def test_single_bracket_produces_one_reference(self):
        refs = _find_references(
            text="See [1] for details.",
            search_context=[_chunk()],
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].name == "Doc.pdf"
        assert refs[0].original_index == [1]
        assert refs[0].sequence_number == 1
        assert refs[0].source == "node-ingestion-chunks"
        assert refs[0].id == "cont_1"
        assert refs[0].message_id == "msg_1"

    def test_multiple_unique_references(self):
        ctx = [
            _chunk(id="cont_1", title="First.pdf"),
            _chunk(id="cont_2", title="Second.pdf"),
        ]
        refs = _find_references(
            text="From [1] and [2].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert len(refs) == 2
        assert refs[0].name == "First.pdf"
        assert refs[0].original_index == [1]
        assert refs[1].name == "Second.pdf"
        assert refs[1].original_index == [2]
        assert refs[0].sequence_number == 1
        assert refs[1].sequence_number == 2

    def test_dedup_same_title_merges_original_index(self):
        ctx = [
            _chunk(id="cont_1", title="Report.pdf", start_page=1, end_page=2),
            _chunk(id="cont_1", title="Report.pdf", start_page=3, end_page=4),
        ]
        refs = _find_references(
            text="See [1] and also [2].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].original_index == [1, 2]

    def test_dedup_with_page_postfix(self):
        ctx = [
            _chunk(id="cont_1", title="Report", start_page=1, end_page=3),
            _chunk(id="cont_1", title="Report", start_page=None, end_page=None),
        ]
        refs = _find_references(
            text="See [1] and [2].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].name == "Report : 1,2,3"
        assert refs[0].original_index == [1, 2]

    def test_out_of_range_bracket_ignored(self):
        refs = _find_references(
            text="See [1] and [99].",
            search_context=[_chunk()],
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].original_index == [1]

    def test_zero_bracket_ignored(self):
        refs = _find_references(
            text="See [0] for details.",
            search_context=[_chunk()],
            message_id="msg_1",
        )

        assert len(refs) == 0

    def test_empty_search_context(self):
        refs = _find_references(
            text="See [1].",
            search_context=[],
            message_id="msg_1",
        )

        assert refs == []

    def test_sequence_number_starts_after_existing_sups(self):
        refs = _find_references(
            text="Already cited<sup>3</sup>. Now [1].",
            search_context=[_chunk()],
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].sequence_number == 4

    def test_external_url_preserved(self):
        ctx = [
            _chunk(
                url="https://example.com/page",
                internally_stored_at=None,
            )
        ]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert refs[0].url == "https://example.com/page"

    def test_internally_stored_uses_unique_url(self):
        ctx = [
            _chunk(
                id="cont_stored",
                url="https://example.com/stored",
                internally_stored_at=datetime(2024, 7, 22),
            )
        ]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert refs[0].url == "unique://content/cont_stored"

    def test_source_id_without_chunk_id(self):
        ctx = [_chunk(id="cont_only", chunk_id=None)]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert refs[0].source_id == "cont_only"

    def test_source_id_with_chunk_id(self):
        ctx = [_chunk(id="cont_1", chunk_id="chunk_abc")]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert refs[0].source_id == "cont_1_chunk_abc"

    def test_falls_back_to_key_when_no_title(self):
        ctx = [_chunk(title=None, key="document.pdf")]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert refs[0].name == "document.pdf"

    def test_no_title_or_key_still_produces_reference(self):
        ctx = [_chunk(id="cont_xyz", title=None, key=None)]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].id == "cont_xyz"
        assert refs[0].name == ""
