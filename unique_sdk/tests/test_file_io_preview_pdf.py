"""Unit tests for the preview-PDF upload path in
``unique_sdk.utils.file_io.upload_file``.

These tests pin the contract that the user-facing one-call upload
shape covers the Office → PDF preview flow:

* ``previewPdfFileName`` is forwarded into both upsert calls (the
  ``writeUrl`` round and the post-upload ``byteSize`` round) so the
  Content row in node-ingestion stores the preview filename
  consistently.
* The PDF blob is PUT to the SAS URL the server returned on the
  first upsert; nothing more, nothing less.
* Skipping ``preview_pdf_path`` keeps the legacy single-blob
  behaviour (no ``previewPdfFileName``, no preview PUT) — important
  because we don't want to regress every existing call site that
  uses ``upload_file`` purely for an original-only upload.
* A missing ``pdfPreviewWriteUrl`` on the response is treated as a
  hard error rather than silently dropping the preview, so
  server-side regressions surface immediately.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from unique_sdk.utils import file_io


@pytest.fixture
def sample_pptx(tmp_path: Any) -> str:
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"fake-pptx-bytes")
    return str(pptx)


@pytest.fixture
def sample_pdf(tmp_path: Any) -> str:
    pdf = tmp_path / "deck-rendered.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    return str(pdf)


def _fake_created_content(**overrides: Any) -> MagicMock:
    content = MagicMock()
    content.writeUrl = "https://blob.example/write-original?sig=1"
    content.readUrl = "https://blob.example/read-original?sig=1"
    content.pdfPreviewWriteUrl = "https://blob.example/write-preview?sig=2"
    for key, value in overrides.items():
        setattr(content, key, value)
    return content


class TestUploadFilePreviewPdfPath:
    def test_skipping_preview_keeps_legacy_behaviour(self, sample_pptx: str) -> None:
        """Without ``preview_pdf_path``, no preview filename is registered
        and only the original blob is PUT — same as the SDK shipped
        for years."""
        created = _fake_created_content()
        upsert_calls: list[dict[str, Any]] = []

        def upsert(**kwargs: Any) -> Any:
            upsert_calls.append(kwargs)
            return created

        put_mock = MagicMock(return_value=MagicMock(status_code=200))

        with (
            patch.object(file_io.Content, "upsert", side_effect=upsert),
            patch.object(file_io.unique_sdk.Content, "upsert", side_effect=upsert),
            patch.object(file_io.requests, "put", put_mock),
        ):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_pptx,
                displayed_filename="deck.pptx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                chat_id="chat-1",
            )

        for call in upsert_calls:
            assert call.get("previewPdfFileName") is None
        # Only one PUT — for the original blob; no preview PUT.
        assert put_mock.call_count == 1
        original_put = put_mock.call_args_list[0]
        assert original_put.args[0] == created.writeUrl

    def test_preview_pdf_path_uploads_both_blobs_and_registers_preview(
        self, sample_pptx: str, sample_pdf: str
    ) -> None:
        """With ``preview_pdf_path``, the SDK registers the preview
        filename on the upserted content, PUTs the original to
        ``writeUrl``, then PUTs the PDF to ``pdfPreviewWriteUrl``."""
        created = _fake_created_content()
        upsert_calls: list[dict[str, Any]] = []

        def upsert(**kwargs: Any) -> Any:
            upsert_calls.append(kwargs)
            return created

        put_mock = MagicMock(return_value=MagicMock(status_code=200))

        with (
            patch.object(file_io.Content, "upsert", side_effect=upsert),
            patch.object(file_io.unique_sdk.Content, "upsert", side_effect=upsert),
            patch.object(file_io.requests, "put", put_mock),
        ):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_pptx,
                displayed_filename="deck.pptx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                chat_id="chat-1",
                preview_pdf_path=sample_pdf,
            )

        # Both upserts include the same derived preview filename so the
        # Content row settles on a deterministic blob name.
        assert len(upsert_calls) == 2
        for call in upsert_calls:
            assert call["previewPdfFileName"] == "deck_preview.pdf"

        # Two PUTs: original first (writeUrl), preview second
        # (pdfPreviewWriteUrl). Order matters — preview PUT must run
        # after the upsert mints the SAS URL.
        assert put_mock.call_count == 2
        assert put_mock.call_args_list[0].args[0] == created.writeUrl
        assert put_mock.call_args_list[1].args[0] == created.pdfPreviewWriteUrl
        preview_headers = put_mock.call_args_list[1].kwargs.get("headers", {})
        assert preview_headers.get("X-Ms-Blob-Content-Type") == "application/pdf"
        assert preview_headers.get("X-Ms-Blob-Type") == "BlockBlob"

    def test_explicit_preview_pdf_filename_overrides_default(
        self, sample_pptx: str, sample_pdf: str
    ) -> None:
        """An explicit ``preview_pdf_filename`` wins over the
        ``<stem>_preview.pdf`` default, which lets callers store
        previews under a name that matches their archival scheme."""
        created = _fake_created_content()
        upsert_calls: list[dict[str, Any]] = []

        def upsert(**kwargs: Any) -> Any:
            upsert_calls.append(kwargs)
            return created

        with (
            patch.object(file_io.Content, "upsert", side_effect=upsert),
            patch.object(file_io.unique_sdk.Content, "upsert", side_effect=upsert),
            patch.object(
                file_io.requests,
                "put",
                MagicMock(return_value=MagicMock(status_code=200)),
            ),
        ):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_pptx,
                displayed_filename="deck.pptx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                chat_id="chat-1",
                preview_pdf_path=sample_pdf,
                preview_pdf_filename="custom-archive-name.pdf",
            )

        for call in upsert_calls:
            assert call["previewPdfFileName"] == "custom-archive-name.pdf"

    def test_missing_preview_write_url_raises(
        self, sample_pptx: str, sample_pdf: str
    ) -> None:
        """The server only mints ``pdfPreviewWriteUrl`` when
        ``previewPdfFileName`` reaches the upsert resolver. If the
        response is missing the URL, the server is misconfigured —
        surface the error instead of silently dropping the preview."""
        created = _fake_created_content(pdfPreviewWriteUrl=None)

        with (
            patch.object(file_io.Content, "upsert", return_value=created),
            patch.object(file_io.unique_sdk.Content, "upsert", return_value=created),
            patch.object(
                file_io.requests,
                "put",
                MagicMock(return_value=MagicMock(status_code=200)),
            ),
            pytest.raises(RuntimeError, match="pdfPreviewWriteUrl"),
        ):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_pptx,
                displayed_filename="deck.pptx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                chat_id="chat-1",
                preview_pdf_path=sample_pdf,
            )

    def test_missing_preview_path_raises(self, sample_pptx: str) -> None:
        """A non-existent ``preview_pdf_path`` is a programmer mistake
        — fail before touching the network so the caller knows
        immediately."""
        with pytest.raises(ValueError, match="preview_pdf_path"):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_pptx,
                displayed_filename="deck.pptx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                chat_id="chat-1",
                preview_pdf_path="/definitely/not/a/real/file.pdf",
            )

    def test_preview_filename_without_path_raises(self, sample_pptx: str) -> None:
        """Passing ``preview_pdf_filename`` without ``preview_pdf_path``
        would register a phantom preview on the Content row but never
        upload any bytes (because the PUT is gated on the path). Treat
        the inconsistent argument combo as a programmer mistake and
        refuse before touching the network."""
        with pytest.raises(ValueError, match="preview_pdf_filename"):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_pptx,
                displayed_filename="deck.pptx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                chat_id="chat-1",
                preview_pdf_filename="orphan.pdf",
            )


class TestDerivePreviewPdfFilename:
    @pytest.mark.parametrize(
        "displayed,expected",
        [
            ("deck.pptx", "deck_preview.pdf"),
            ("Quarterly Report.docx", "Quarterly Report_preview.pdf"),
            ("noext", "noext_preview.pdf"),
            ("multi.dot.name.xlsx", "multi.dot.name_preview.pdf"),
        ],
    )
    def test_derives_predictable_blob_name(self, displayed: str, expected: str) -> None:
        assert file_io._derive_preview_pdf_filename(displayed) == expected
