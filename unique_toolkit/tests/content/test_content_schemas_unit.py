from datetime import datetime, timedelta, timezone

import pytest

from unique_toolkit.content.schemas import Content, ContentChunk, ContentReference

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_content(**kwargs) -> Content:
    """Minimal Content with only the fields relevant to is_ingested."""
    defaults = {"id": "cont_abc", "key": "file.pdf"}
    return Content(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Content.is_ingested
# ---------------------------------------------------------------------------


@pytest.mark.ai
class TestContentIsIngested:
    def test__returns_default_default_if_unknown__when_applied_ingestion_config_is_none(
        self,
    ):
        """
        Purpose: Verify is_ingested returns the default default_if_unknown (True) when
                 applied_ingestion_config is None.
        Why this matters: Callers rely on the default to mean "assume ingested" when
                          no config metadata is present (e.g. legacy content).
        Setup summary: Content with applied_ingestion_config=None; assert True is returned.
        """
        content = make_content(applied_ingestion_config=None)

        assert content.is_ingested() is True

    @pytest.mark.parametrize("default_if_unknown", [True, False])
    def test__returns_custom_default_if_unknown__when_applied_ingestion_config_is_none(
        self, default_if_unknown: bool
    ):
        """
        Purpose: Verify is_ingested honours a caller-supplied default_if_unknown when
                 applied_ingestion_config is None.
        Why this matters: Some call sites need a conservative False default to avoid
                          treating missing config as "ingested".
        Setup summary: Content with applied_ingestion_config=None; parametrise
                       default_if_unknown; assert the exact value is echoed back.
        """
        content = make_content(applied_ingestion_config=None)

        assert (
            content.is_ingested(default_if_unknown=default_if_unknown)
            is default_if_unknown
        )

    def test__returns_default_default_if_unknown__when_uniqueIngestionMode_key_missing(
        self,
    ):
        """
        Purpose: Verify is_ingested returns the default default_if_unknown (True) when
                 applied_ingestion_config exists but lacks the uniqueIngestionMode key.
        Why this matters: A config dict that was populated with other keys but not the
                          mode key is functionally equivalent to "undefined" for this check.
        Setup summary: Content with a config dict that omits uniqueIngestionMode;
                       assert True is returned.
        """
        content = make_content(applied_ingestion_config={"chunkStrategy": "default"})

        assert content.is_ingested() is True

    @pytest.mark.parametrize("default_if_unknown", [True, False])
    def test__returns_custom_default_if_unknown__when_uniqueIngestionMode_key_missing(
        self, default_if_unknown: bool
    ):
        """
        Purpose: Verify is_ingested honours a caller-supplied default_if_unknown when the
                 uniqueIngestionMode key is absent from applied_ingestion_config.
        Why this matters: Consistent behaviour regardless of which "undefined" branch is hit.
        Setup summary: Config dict without uniqueIngestionMode; parametrise default_if_unknown;
                       assert the exact value is echoed back.
        """
        content = make_content(applied_ingestion_config={"chunkStrategy": "default"})

        assert (
            content.is_ingested(default_if_unknown=default_if_unknown)
            is default_if_unknown
        )

    def test__returns_false__when_uniqueIngestionMode_is_SKIP_INGESTION(self):
        """
        Purpose: Verify is_ingested returns False when uniqueIngestionMode is SKIP_INGESTION.
        Why this matters: SKIP_INGESTION signals that content was deliberately not ingested;
                          callers must not treat it as available for retrieval.
        Setup summary: Config with uniqueIngestionMode=SKIP_INGESTION; assert False.
        """
        content = make_content(
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_INGESTION"}
        )

        assert content.is_ingested() is False

    def test__returns_default_if_unknown__when_SKIP_EXCEL_INGESTION_and_no_mime_type(
        self,
    ):
        """
        SKIP_EXCEL_INGESTION without a mime_type is ambiguous — we cannot tell
        whether the file is an Excel/CSV file, so return default_if_unknown.
        """
        content = make_content(
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_EXCEL_INGESTION"}
        )

        assert content.is_ingested() is True
        assert content.is_ingested(default_if_unknown=False) is False

    @pytest.mark.parametrize(
        "mime_type",
        [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
            "application/vnd.ms-excel",  # xls
            "text/csv",
        ],
    )
    def test__returns_false__when_SKIP_EXCEL_INGESTION_and_excel_or_csv_mime(
        self, mime_type: str
    ):
        """
        SKIP_EXCEL_INGESTION with an Excel or CSV mime type means the file was
        intentionally skipped — not ingested.
        """
        content = make_content(
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_EXCEL_INGESTION"},
            mime_type=mime_type,
        )

        assert content.is_ingested() is False

    @pytest.mark.parametrize(
        "mime_type",
        [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ],
    )
    def test__returns_true__when_SKIP_EXCEL_INGESTION_and_non_excel_mime(
        self, mime_type: str
    ):
        """
        SKIP_EXCEL_INGESTION only skips Excel/CSV files; non-Excel content with
        this mode is still ingested.
        """
        content = make_content(
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_EXCEL_INGESTION"},
            mime_type=mime_type,
        )

        assert content.is_ingested() is True

    def test__returns_default_if_unknown__when_SKIP_EXCEL_INGESTION_and_unknown_mime(
        self,
    ):
        """
        An unrecognised mime string cannot be classified, so fall back to
        default_if_unknown.
        """
        content = make_content(
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_EXCEL_INGESTION"},
            mime_type="application/x-totally-unknown",
        )

        assert content.is_ingested() is True
        assert content.is_ingested(default_if_unknown=False) is False

    @pytest.mark.parametrize(
        "mode",
        [
            "STANDARD",
            "FULL",
            "CHUNKED",
            "some_future_mode",
        ],
    )
    def test__returns_true__when_uniqueIngestionMode_is_an_ingested_mode(
        self, mode: str
    ):
        """
        Purpose: Verify is_ingested returns True for any mode that is not in the
                 skip-list (SKIP_INGESTION, SKIP_EXCEL_INGESTION).
        Why this matters: New ingestion modes should be considered "ingested" by default
                          without requiring code changes.
        Setup summary: Parametrise over several non-skip mode strings; assert True for each.
        """
        content = make_content(applied_ingestion_config={"uniqueIngestionMode": mode})

        assert content.is_ingested() is True

    def test__default_if_unknown_arg_is_keyword_only(self):
        """
        Purpose: Verify that default_if_unknown cannot be passed as a positional argument.
        Why this matters: The method signature uses * to enforce keyword-only; passing
                          it positionally would be a caller error that Python should reject.
        Setup summary: Call is_ingested with a positional argument; assert TypeError raised.
        """
        content = make_content(applied_ingestion_config=None)

        with pytest.raises(TypeError):
            content.is_ingested(False)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Content.is_expired
# ---------------------------------------------------------------------------


@pytest.mark.ai
class TestContentIsExpired:
    def test__returns_false__when_expired_at_is_none(self):
        """
        Purpose: Verify is_expired returns False when expired_at is None.
        Why this matters: None means no expiry is set — the content is permanently valid.
        Setup summary: Content with expired_at=None; assert False.
        """
        content = make_content(expired_at=None)

        assert content.is_expired() is False

    def test__returns_false__when_expired_at_is_in_the_future(self):
        """
        Purpose: Verify is_expired returns False when expired_at is in the future.
        Why this matters: Content whose expiry is in the future is still valid and
                          should not be treated as expired.
        Setup summary: Content with expired_at = now + 1 day; assert False.
        """
        future = datetime.now(timezone.utc) + timedelta(days=1)
        content = make_content(expired_at=future)

        assert content.is_expired() is False

    def test__returns_true__when_expired_at_is_in_the_past(self):
        """
        Purpose: Verify is_expired returns True when expired_at is in the past.
        Why this matters: Content whose expiry has passed is stale and callers must
                          treat it as unavailable.
        Setup summary: Content with expired_at = now - 1 day; assert True.
        """
        past = datetime.now(timezone.utc) - timedelta(days=1)
        content = make_content(expired_at=past)

        assert content.is_expired() is True

    def test__returns_true__when_expired_at_is_just_past_current_moment(self):
        """
        Purpose: Verify is_expired returns True when expired_at is just one second ago.
        Why this matters: The boundary condition (expired_at <= now) must be honoured
                          so that content is considered expired the instant its time passes.
        Setup summary: Content with expired_at = now - 1 second; assert True.
        """
        just_past = datetime.now(timezone.utc) - timedelta(seconds=1)
        content = make_content(expired_at=just_past)

        assert content.is_expired() is True


# ---------------------------------------------------------------------------
# ContentChunk.to_reference
# ---------------------------------------------------------------------------


class TestContentReferenceUrlOptional:
    def test_url_can_be_omitted(self):
        ref = ContentReference(
            name="crm · get_account",
            sequence_number=1,
            source="mcp:crm",
            source_id="mcp_abc_mcp_abc",
        )
        assert ref.url is None

    def test_url_still_accepted_when_present(self):
        ref = ContentReference(
            name="Example",
            sequence_number=1,
            source="mcp:kb",
            source_id="mcp_def_mcp_def",
            url="https://example.com",
        )
        assert ref.url == "https://example.com"


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
        assert ref.original_index == []

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

    def test_does_not_double_pages_postfix_when_title_already_includes_it(self):
        chunk = ContentChunk(
            id="cont_sorted",
            chunk_id="chunk_s",
            title="Annual Report : 1,2,3",
            text="text",
            order=1,
            start_page=1,
            end_page=3,
        )

        ref = chunk.to_reference(sequence_number=1)

        assert ref.name == "Annual Report : 1,2,3"
        assert ref.name.count(" : 1,2,3") == 1

    def test_does_not_double_postfix_after_merge_with_non_contiguous_pages(self):
        """After merge_content_chunks, title may carry a non-contiguous postfix
        (e.g. " : 1,2,5,8,9") while start_page/end_page span a contiguous
        range (1..9). The dedup check must still prevent a second postfix."""
        chunk = ContentChunk(
            id="cont_merged",
            chunk_id="chunk_m",
            title="Report : 1,2,5,8,9",
            text="text",
            order=1,
            start_page=1,
            end_page=9,
        )

        ref = chunk.to_reference(sequence_number=1)

        assert " : " not in ref.name.replace("Report : 1,2,5,8,9", "", 1)
        assert ref.name == "Report : 1,2,5,8,9"
