"""Unit tests for UN-23833: unchecked/unbounded blob transfers in
``unique_sdk.utils.file_io``.

Covers:
* ``upload_file``'s blob PUT now raises on a failed status code instead
  of silently falling through to the finalize upsert (which would flip
  the Content row to "bytes on blob" over an empty/failed upload).
* All four direct ``requests`` calls in this module (``upload_file``'s
  PUT, ``_put_preview_pdf``'s PUT, ``download_file``'s GET,
  ``download_content``'s GET) now pass a timeout.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import unique_sdk
from unique_sdk.utils import file_io


def _fake_response(status_code: int = 200, **extra: Any) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    # Downloads stream the body: support context-manager use + iter_content.
    body = extra.get("content", b"")
    response.iter_content.side_effect = lambda chunk_size: iter([body])
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    for key, value in extra.items():
        setattr(response, key, value)
    return response


def _fake_created_content(**overrides: Any) -> MagicMock:
    content = MagicMock()
    content.id = "cont_test_1"
    content.writeUrl = "https://blob.example/write?sig=1"
    content.readUrl = "https://blob.example/read?sig=1"
    for key, value in overrides.items():
        setattr(content, key, value)
    return content


@pytest.fixture
def sample_file(tmp_path: Any) -> str:
    path = tmp_path / "report.xlsx"
    path.write_bytes(b"fake-xlsx-bytes")
    return str(path)


@pytest.mark.ai
@pytest.mark.unit
class TestUploadFilePutErrorHandling:
    def test_failed_put_raises_and_skips_finalize_upsert(
        self, sample_file: str
    ) -> None:
        """A non-2xx PUT must raise instead of letting the finalize
        upsert mark the row bytes-on-blob over a failed upload."""
        created = _fake_created_content()
        upsert_mock = MagicMock(return_value=created)

        with (
            patch.object(file_io.Content, "upsert", upsert_mock),
            patch.object(
                file_io.requests,
                "put",
                MagicMock(return_value=_fake_response(status_code=500, text="oops")),
            ),
            pytest.raises(RuntimeError, match="500"),
        ):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_file,
                displayed_filename="report.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                chat_id="chat-1",
            )

        # Only the first (pre-PUT) upsert ran; the finalize upsert that
        # would set byteSize/fileUrl must not have been reached.
        upsert_mock.assert_called_once()

    def test_successful_put_proceeds_to_finalize_upsert(self, sample_file: str) -> None:
        """A 2xx PUT must still finalize as before — this is a
        regression guard, not new behaviour."""
        created = _fake_created_content()
        upsert_mock = MagicMock(return_value=created)

        with (
            patch.object(file_io.Content, "upsert", upsert_mock),
            patch.object(
                file_io.requests,
                "put",
                MagicMock(return_value=_fake_response(status_code=201)),
            ),
        ):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_file,
                displayed_filename="report.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                chat_id="chat-1",
            )

        assert upsert_mock.call_count == 2


@pytest.mark.ai
@pytest.mark.unit
class TestBlobTransferTimeouts:
    def test_upload_file_put_passes_timeout(self, sample_file: str) -> None:
        created = _fake_created_content()
        put_mock = MagicMock(return_value=_fake_response(status_code=200))

        with (
            patch.object(file_io.Content, "upsert", return_value=created),
            patch.object(file_io.requests, "put", put_mock),
        ):
            file_io.upload_file(
                userId="user-1",
                companyId="company-1",
                path_to_file=sample_file,
                displayed_filename="report.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                chat_id="chat-1",
            )

        assert put_mock.call_args.kwargs["timeout"] == unique_sdk.blob_transfer_timeout

    def test_put_preview_pdf_passes_timeout(self, tmp_path: Any) -> None:
        pdf_path = tmp_path / "preview.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")
        put_mock = MagicMock(return_value=_fake_response(status_code=200))

        with patch.object(file_io.requests, "put", put_mock):
            file_io._put_preview_pdf(
                "https://blob.example/write-preview?sig=1", str(pdf_path)
            )

        assert put_mock.call_args.kwargs["timeout"] == unique_sdk.blob_transfer_timeout

    def test_download_file_get_passes_timeout(self) -> None:
        get_mock = MagicMock(
            return_value=_fake_response(status_code=200, content=b"data")
        )

        with patch.object(file_io.requests, "get", get_mock):
            file_io.download_file("https://blob.example/read?sig=1", "out.bin")

        assert get_mock.call_args.kwargs["timeout"] == unique_sdk.blob_transfer_timeout

    def test_download_content_get_passes_timeout(self, tmp_path: Any) -> None:
        get_mock = MagicMock(
            return_value=_fake_response(status_code=200, content=b"data")
        )

        with patch.object(file_io.requests, "get", get_mock):
            file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="ignored.bin",
                target_path=tmp_path / "out.bin",
            )

        assert get_mock.call_args.kwargs["timeout"] == unique_sdk.blob_transfer_timeout
