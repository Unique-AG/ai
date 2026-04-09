from datetime import datetime

import pytest

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
    @pytest.mark.ai
    def test_find_references__single_bracket__produces_one_reference(self):
        """
        Purpose: Verifies that a single [1] bracket in the text produces exactly
        one ContentReference with correct fields populated.
        Why this matters: This is the fundamental happy-path; if single-bracket
        extraction fails, no references will ever appear in the frontend.
        Setup summary: Pass text with [1] and one chunk; assert the returned
        reference has the expected name, index, sequence_number, source, id,
        and message_id.
        """
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

    @pytest.mark.ai
    def test_find_references__multiple_brackets__produces_distinct_references(self):
        """
        Purpose: Verifies that [1] and [2] pointing to chunks with different
        titles produce two separate references with incrementing sequence numbers.
        Why this matters: Messages routinely cite multiple sources; failing to
        produce distinct references would collapse citations in the frontend.
        Setup summary: Two chunks with different titles, text with [1][2];
        assert two references with correct names, indices, and sequence numbers.
        """
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

    @pytest.mark.ai
    def test_find_references__same_title__merges_original_index(self):
        """
        Purpose: Verifies that two brackets pointing to chunks with the same
        title are deduplicated into a single reference with both indices.
        Why this matters: Without dedup the frontend would show duplicate
        reference chips for the same document.
        Setup summary: Two chunks with identical title, text with [1][2];
        assert one reference whose original_index contains both 1 and 2.
        """
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

    @pytest.mark.ai
    def test_find_references__page_postfix_dedup__merges_into_first(self):
        """
        Purpose: Verifies that a reference whose name includes a page postfix
        (e.g. "Report : 1,2,3") still deduplicates against the base name
        "Report" when a second chunk with the same title has no pages.
        Why this matters: The PR introduced startswith-based dedup; without it,
        two chunks from the same document with different page ranges would
        create duplicate reference chips.
        Setup summary: First chunk has pages 1-3, second has no pages, same
        title; assert one reference with the page postfix and both indices.
        """
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

    @pytest.mark.ai
    def test_find_references__out_of_range_bracket__ignored(self):
        """
        Purpose: Verifies that a bracket index exceeding the search context
        length is silently skipped.
        Why this matters: LLMs sometimes hallucinate bracket numbers beyond
        the provided sources; these must not cause index errors or ghost refs.
        Setup summary: Text has [1] (valid) and [99] (out of range) with one
        chunk; assert only one reference is produced.
        """
        refs = _find_references(
            text="See [1] and [99].",
            search_context=[_chunk()],
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].original_index == [1]

    @pytest.mark.ai
    def test_find_references__zero_bracket__ignored(self):
        """
        Purpose: Verifies that [0] is skipped because brackets are 1-based,
        making index 0 map to -1 which is out of range.
        Why this matters: A zero bracket must not produce a reference or cause
        a negative-index lookup into the search context.
        Setup summary: Text with [0] and one chunk; assert no references.
        """
        refs = _find_references(
            text="See [0] for details.",
            search_context=[_chunk()],
            message_id="msg_1",
        )

        assert len(refs) == 0

    @pytest.mark.ai
    def test_find_references__empty_search_context__returns_empty(self):
        """
        Purpose: Verifies that an empty search context produces no references
        regardless of bracket numbers in the text.
        Why this matters: Some messages have no search results; the function
        must not error or produce phantom references.
        Setup summary: Text with [1] but empty context list; assert empty.
        """
        refs = _find_references(
            text="See [1].",
            search_context=[],
            message_id="msg_1",
        )

        assert refs == []

    @pytest.mark.ai
    def test_find_references__existing_sups__sequence_continues(self):
        """
        Purpose: Verifies that sequence_number starts after the highest
        existing <sup> number already in the text.
        Why this matters: When a message already has superscript references
        (e.g. from a prior streaming pass), new references must not collide
        with existing footnote numbers.
        Setup summary: Text has <sup>3</sup> already and [1]; assert the new
        reference gets sequence_number 4.
        """
        refs = _find_references(
            text="Already cited<sup>3</sup>. Now [1].",
            search_context=[_chunk()],
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].sequence_number == 4

    @pytest.mark.ai
    def test_find_references__external_url__preserved_on_reference(self):
        """
        Purpose: Verifies that a chunk with an external URL and no
        internally_stored_at uses the chunk's own URL on the reference.
        Why this matters: Web-sourced content must link to the original page,
        not to the internal unique:// scheme.
        Setup summary: Chunk with url set and internally_stored_at=None;
        assert the reference URL matches the chunk URL.
        """
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

    @pytest.mark.ai
    def test_find_references__internally_stored__uses_unique_url(self):
        """
        Purpose: Verifies that a chunk with internally_stored_at set falls
        back to the unique://content/{id} URL even when url is present.
        Why this matters: Internally stored documents must be fetched via the
        platform content API, not via the original upload URL which may have
        expired or be inaccessible.
        Setup summary: Chunk with both url and internally_stored_at set;
        assert the reference URL is unique://content/{id}.
        """
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

    @pytest.mark.ai
    def test_find_references__no_chunk_id__source_id_is_content_id(self):
        """
        Purpose: Verifies that when chunk_id is None the source_id falls back
        to the content id alone without a trailing underscore.
        Why this matters: The frontend uses source_id for reference lookup;
        a malformed id would break the highlight-on-click flow.
        Setup summary: Chunk with chunk_id=None; assert source_id equals the
        content id.
        """
        ctx = [_chunk(id="cont_only", chunk_id=None)]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert refs[0].source_id == "cont_only"

    @pytest.mark.ai
    def test_find_references__with_chunk_id__source_id_is_composite(self):
        """
        Purpose: Verifies that when chunk_id is present the source_id is
        "{content_id}_{chunk_id}".
        Why this matters: The backend ReferenceService looks up references by
        this composite key; a wrong format would return no match.
        Setup summary: Chunk with both id and chunk_id; assert source_id is
        the two ids joined by underscore.
        """
        ctx = [_chunk(id="cont_1", chunk_id="chunk_abc")]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert refs[0].source_id == "cont_1_chunk_abc"

    @pytest.mark.ai
    def test_find_references__no_title__falls_back_to_key(self):
        """
        Purpose: Verifies that when title is None the reference name uses the
        chunk key instead.
        Why this matters: Some ingested content has no title metadata; the
        reference chip must still show a meaningful label.
        Setup summary: Chunk with title=None and key="document.pdf"; assert
        the reference name is the key.
        """
        ctx = [_chunk(title=None, key="document.pdf")]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert refs[0].name == "document.pdf"

    @pytest.mark.ai
    def test_find_references__no_title_or_key__uses_content_id_fallback_name(self):
        """
        Purpose: Verifies that when both title and key are None the reference
        is still created with a stable display name derived from the content id.
        Why this matters: Matches dedup logic in _find_references and avoids
        empty reference names.
        Setup summary: Chunk with title=None and key=None; assert one reference
        with name ``Content {id}`` and correct id/message_id.
        """
        ctx = [_chunk(id="cont_xyz", title=None, key=None)]
        refs = _find_references(
            text="See [1].",
            search_context=ctx,
            message_id="msg_1",
        )

        assert len(refs) == 1
        assert refs[0].id == "cont_xyz"
        assert refs[0].message_id == "msg_1"
        assert refs[0].name == "Content cont_xyz"
