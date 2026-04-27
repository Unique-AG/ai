"""Unit tests for the preview-PDF upload path in
``unique_sdk.utils.file_io.upload_file``.

These tests pin the contract that the user-facing one-call upload
shape covers the Office → PDF preview flow with the platform's
``${content.id}_pdfPreview`` blob naming convention:

* The first upsert is sent WITHOUT ``previewPdfFileName`` so the SDK
  can read the freshly-minted content id from the response. Deriving
  the preview blob name from the user-supplied ``displayed_filename``
  before the round-trip would race across uploads with the same key
  (two ``report.pptx`` uploads in the same company would overwrite
  each other's preview blob).
* The finalize upsert (the one that flips the row to
  ``byteSize`` + ``fileUrl``) carries
  ``previewPdfFileName = f"{content.id}_pdfPreview"`` — the same
  convention used by the platform's ingestion worker so blob names
  match across all clients of node-ingestion.
* The PDF blob is PUT to the SAS URL the **finalize** response
  returned (not the first one — only the upsert that carries
  ``previewPdfFileName`` can mint a ``pdfPreviewWriteUrl``).
* Skipping ``preview_pdf_path`` keeps the legacy single-blob
  behaviour (no ``previewPdfFileName``, no preview PUT).
* A missing ``pdfPreviewWriteUrl`` on the finalize response is
  treated as a hard error rather than silently dropping the preview,
  so server-side regressions surface immediately.
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
    """Build a stand-in for the typed ``Content`` upsert response.

    A deterministic ``id`` is essential because the SDK derives the
    preview blob name from it (``f"{content.id}_pdfPreview"``); a
    bare ``MagicMock()`` ``id`` would assert against an opaque mock
    repr and miss the actual contract under test.
    """
    content = MagicMock()
    content.id = "cont_test_pptx_1"
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

        # Key must be *absent* (not present-as-None) on every upsert: an
        # explicit ``"previewPdfFileName": null`` in the JSON body would
        # tell the server to clear an existing preview, silently
        # regressing callers who re-upload content that already has one.
        for call in upsert_calls:
            assert "previewPdfFileName" not in call
        # Only one PUT — for the original blob; no preview PUT.
        assert put_mock.call_count == 1
        original_put = put_mock.call_args_list[0]
        assert original_put.args[0] == created.writeUrl

    def test_preview_pdf_path_uploads_both_blobs_with_content_id_naming(
        self, sample_pptx: str, sample_pdf: str
    ) -> None:
        """With ``preview_pdf_path``, the SDK:

        1. Issues the first upsert WITHOUT ``previewPdfFileName`` so
           the freshly-minted content id can be read from the response.
        2. PUTs the original blob to ``writeUrl``.
        3. Issues the finalize upsert WITH
           ``previewPdfFileName = f"{content.id}_pdfPreview"`` — same
           convention as the platform's ingestion worker.
        4. PUTs the preview PDF to the ``pdfPreviewWriteUrl`` the
           finalize response carries.
        """
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

        # Two upserts: first without the preview name, finalize with it.
        assert len(upsert_calls) == 2

        # First upsert MUST NOT carry ``previewPdfFileName``: the id is
        # not known yet, and shipping any other value would land the
        # blob at a key the platform would have to migrate later.
        assert "previewPdfFileName" not in upsert_calls[0]
        # First upsert is also the "create or update by key" round —
        # no ``byteSize`` / ``fileUrl`` yet.
        assert "byteSize" not in upsert_calls[0]["input"]
        assert "fileUrl" not in upsert_calls[0]

        # Finalize upsert carries the content-id-derived preview name
        # AND the byteSize/fileUrl that mark the row bytes-on-blob.
        assert upsert_calls[1]["previewPdfFileName"] == f"{created.id}_pdfPreview"
        assert upsert_calls[1]["input"]["byteSize"] > 0
        assert upsert_calls[1]["fileUrl"] == created.readUrl

        # Two PUTs: original first (writeUrl), preview second
        # (pdfPreviewWriteUrl). Order matters — preview PUT must run
        # AFTER the finalize upsert mints the SAS URL.
        assert put_mock.call_count == 2
        assert put_mock.call_args_list[0].args[0] == created.writeUrl
        assert put_mock.call_args_list[1].args[0] == created.pdfPreviewWriteUrl
        preview_headers = put_mock.call_args_list[1].kwargs.get("headers", {})
        assert preview_headers.get("X-Ms-Blob-Content-Type") == "application/pdf"
        assert preview_headers.get("X-Ms-Blob-Type") == "BlockBlob"

    def test_preview_pdf_path_with_scope_id_uses_same_naming(
        self, sample_pptx: str, sample_pdf: str
    ) -> None:
        """The ``${content.id}_pdfPreview`` convention must apply on
        the scope-id branch too — both flows funnel through the same
        finalize upsert and must derive the blob name identically."""
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
                scope_or_unique_path="scope_kb_demo",
                preview_pdf_path=sample_pdf,
            )

        assert len(upsert_calls) == 2
        assert "previewPdfFileName" not in upsert_calls[0]
        assert upsert_calls[1]["previewPdfFileName"] == f"{created.id}_pdfPreview"
        assert upsert_calls[1]["scopeId"] == "scope_kb_demo"

    def test_missing_preview_write_url_raises(
        self, sample_pptx: str, sample_pdf: str
    ) -> None:
        """The server only mints ``pdfPreviewWriteUrl`` when
        ``previewPdfFileName`` reaches the upsert resolver. If the
        finalize response is missing the URL, the server is
        misconfigured — surface the error instead of silently dropping
        the preview."""
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

    def test_absent_preview_write_url_attribute_raises_runtime_error(
        self, sample_pptx: str, sample_pdf: str
    ) -> None:
        """An older gateway may omit ``pdfPreviewWriteUrl`` entirely
        from the finalize upsert response. ``UniqueObject.__getattr__``
        would normally surface that as ``AttributeError``, which would
        skip the descriptive ``RuntimeError`` guard. We must still
        surface the same actionable error so callers can diagnose a
        stale gateway without reading a traceback into ``__getattr__``.
        """

        class _ResponseWithoutPreviewUrl:
            id = "cont_test_pptx_2"
            writeUrl = "https://blob.example/write-original?sig=1"
            readUrl = "https://blob.example/read-original?sig=1"

            def __getattr__(self, name: str) -> Any:  # mimic UniqueObject
                raise AttributeError(name)

        created = _ResponseWithoutPreviewUrl()

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
