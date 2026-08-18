"""Tests for Office PDF preview upload on code-interpreter artifacts."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai.types.responses.response_output_text import AnnotationContainerFileCitation

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors import (
    artifacts as artifacts_mod,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors import (
    office_preview as preview_mod,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.artifacts import (
    save_code_execution_artifact,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.office_preview import (
    office_extension,
)


class _FakeChatService:
    _user_id = "user-1"
    _company_id = "company-1"
    _chat_id = "chat-1"

    def __init__(self) -> None:
        self.upload_to_chat_from_bytes_async = AsyncMock(
            return_value=SimpleNamespace(id="cont-bytes")
        )


def _make_annotation(filename: str) -> AnnotationContainerFileCitation:
    return AnnotationContainerFileCitation(
        container_id="cntr-1",
        file_id="cfile-1",
        filename=filename,
        start_index=0,
        end_index=10,
        type="container_file_citation",
    )


def _docx_mime() -> str:
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _xlsx_mime() -> str:
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _fake_run_soffice_writes_pdf(
    soffice: str,
    source: Path,
    output_dir: Path,
    logger,
) -> None:
    (output_dir / f"{source.stem}.pdf").write_bytes(b"%PDF-1.4")


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("report.docx", ".docx"),
        ("Report.DOCX", ".docx"),
        ("deck.pptx", ".pptx"),
        ("sheet.xlsx", ".xlsx"),
        ("legacy.doc", ".doc"),
        ("notes.txt", None),
        ("chart.png", None),
        ("report.pdf", None),
    ],
)
def test_office_extension__classifies_filename(
    filename: str, expected: str | None
) -> None:
    """
    Purpose: Verify office_extension recognizes previewable Office suffixes.
    Why this matters: Only Office artifacts take the preview-PDF upload path.
    Setup summary: Call office_extension; assert the suffix or None.
    """
    assert office_extension(filename) == expected


@pytest.mark.asyncio
async def test_save_code_execution_artifact__office_file__uploads_with_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify an Office artifact is uploaded via file_io.upload_file with
    preview_pdf_path set after a successful soffice conversion.
    Why this matters: The chat side panel needs a sibling PDF to preview Word /
    PowerPoint / Excel outputs from the code interpreter.
    Setup summary: Mock soffice present and converting; capture upload_file kwargs.
    """
    upload_calls: list[tuple[tuple, dict]] = []

    def fake_upload_file(*args, **kwargs):
        upload_calls.append((args, kwargs))
        return {
            "id": "cont-preview",
            "key": "random_document.docx",
            "title": "random_document.docx",
            "mimeType": _docx_mime(),
        }

    monkeypatch.setattr(
        preview_mod, "_resolve_soffice_binary", lambda: "/usr/bin/soffice"
    )
    monkeypatch.setattr(preview_mod, "_run_soffice", _fake_run_soffice_writes_pdf)
    monkeypatch.setattr(artifacts_mod.file_io, "upload_file", fake_upload_file)

    chat_service = _FakeChatService()
    content = await save_code_execution_artifact(
        chat_service=chat_service,  # type: ignore[arg-type]
        file=_make_annotation("random_document.docx"),
        file_bytes=b"docx bytes",
    )

    assert content.id == "cont-preview"
    assert len(upload_calls) == 1
    chat_service.upload_to_chat_from_bytes_async.assert_not_called()

    args, kwargs = upload_calls[0]
    assert args[:5] == (
        "user-1",
        "company-1",
        args[2],
        "random_document.docx",
        _docx_mime(),
    )
    assert Path(args[2]).name == "random_document.docx"
    assert kwargs["chat_id"] == "chat-1"
    assert Path(kwargs["preview_pdf_path"]).name == "random_document.pdf"
    assert kwargs["ingestion_config"] == {
        "uniqueIngestionMode": "SKIP_INGESTION",
        "hideInChat": True,
    }
    assert kwargs["metadata"] == {
        "codeExecutionArtifactMetadata": {
            "container_id": "cntr-1",
            "file_id": "cfile-1",
            "filepath": "/mnt/data/random_document.docx",
        }
    }


@pytest.mark.asyncio
async def test_save_code_execution_artifact__xlsx__uploads_with_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify Excel artifacts use the spreadsheet MIME type on preview upload.
    Why this matters: Canonical MIME must not depend on host /etc/mime.types.
    Setup summary: Mock conversion; assert MIME and preview filename for .xlsx.
    """
    upload_calls: list[tuple[tuple, dict]] = []

    def fake_upload_file(*args, **kwargs):
        upload_calls.append((args, kwargs))
        return {
            "id": "cont-xlsx-preview",
            "key": "forecast.xlsx",
            "title": "forecast.xlsx",
            "mimeType": _xlsx_mime(),
        }

    monkeypatch.setattr(
        preview_mod, "_resolve_soffice_binary", lambda: "/usr/bin/soffice"
    )
    monkeypatch.setattr(preview_mod, "_run_soffice", _fake_run_soffice_writes_pdf)
    monkeypatch.setattr(artifacts_mod.file_io, "upload_file", fake_upload_file)

    content = await save_code_execution_artifact(
        chat_service=_FakeChatService(),  # type: ignore[arg-type]
        file=_make_annotation("forecast.xlsx"),
        file_bytes=b"xlsx bytes",
    )

    assert content.id == "cont-xlsx-preview"
    args, kwargs = upload_calls[0]
    assert args[3] == "forecast.xlsx"
    assert args[4] == _xlsx_mime()
    assert Path(kwargs["preview_pdf_path"]).name == "forecast.pdf"


@pytest.mark.asyncio
async def test_save_code_execution_artifact__soffice_absent__falls_back_to_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify missing soffice does not fail the upload; original bytes still go up.
    Why this matters: Preview conversion is best-effort and inert when LibreOffice
    is not in the image.
    Setup summary: Mock soffice missing; assert bytes uploader is used.
    """
    monkeypatch.setattr(preview_mod, "_resolve_soffice_binary", lambda: None)
    upload_file = MagicMock(
        side_effect=AssertionError("upload_file must not be called")
    )
    monkeypatch.setattr(artifacts_mod.file_io, "upload_file", upload_file)

    chat_service = _FakeChatService()
    content = await save_code_execution_artifact(
        chat_service=chat_service,  # type: ignore[arg-type]
        file=_make_annotation("report.docx"),
        file_bytes=b"docx bytes",
    )

    assert content.id == "cont-bytes"
    upload_file.assert_not_called()
    chat_service.upload_to_chat_from_bytes_async.assert_awaited_once()
    _, kwargs = chat_service.upload_to_chat_from_bytes_async.await_args
    assert kwargs["content"] == b"docx bytes"
    assert kwargs["content_name"] == "report.docx"
    assert kwargs["mime_type"] == _docx_mime()
    assert kwargs["skip_ingestion"] is True
    assert kwargs["hide_in_chat"] is True


@pytest.mark.asyncio
async def test_save_code_execution_artifact__conversion_failure__falls_back_to_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a soffice conversion error still uploads the original file.
    Why this matters: A broken Office file must not swallow the download.
    Setup summary: Mock soffice present but raising; assert bytes fallback.
    """

    def failing_soffice(*_args, **_kwargs) -> None:
        raise RuntimeError("LibreOffice crashed")

    monkeypatch.setattr(
        preview_mod, "_resolve_soffice_binary", lambda: "/usr/bin/soffice"
    )
    monkeypatch.setattr(preview_mod, "_run_soffice", failing_soffice)

    chat_service = _FakeChatService()
    content = await save_code_execution_artifact(
        chat_service=chat_service,  # type: ignore[arg-type]
        file=_make_annotation("deck.pptx"),
        file_bytes=b"pptx bytes",
    )

    assert content.id == "cont-bytes"
    chat_service.upload_to_chat_from_bytes_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_code_execution_artifact__preview_upload_failure__falls_back_to_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify upload_file exceptions fall back to the byte uploader.
    Why this matters: A SAS/preview handshake failure must still deliver the file.
    Setup summary: Conversion succeeds; upload_file raises; assert bytes fallback.
    """

    def fake_upload_file(*_args, **_kwargs):
        raise RuntimeError("SAS token denied")

    monkeypatch.setattr(
        preview_mod, "_resolve_soffice_binary", lambda: "/usr/bin/soffice"
    )
    monkeypatch.setattr(preview_mod, "_run_soffice", _fake_run_soffice_writes_pdf)
    monkeypatch.setattr(artifacts_mod.file_io, "upload_file", fake_upload_file)

    chat_service = _FakeChatService()
    content = await save_code_execution_artifact(
        chat_service=chat_service,  # type: ignore[arg-type]
        file=_make_annotation("deck.pptx"),
        file_bytes=b"pptx bytes",
    )

    assert content.id == "cont-bytes"
    chat_service.upload_to_chat_from_bytes_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_code_execution_artifact__non_office__uses_bytes_uploader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify non-Office files skip conversion and use the original byte path.
    Why this matters: PNG/PDF/text artifacts must not invoke soffice or file_io.upload_file.
    Setup summary: Upload notes.txt; assert bytes uploader only.
    """
    upload_file = MagicMock(
        side_effect=AssertionError("upload_file must not be called")
    )
    monkeypatch.setattr(artifacts_mod.file_io, "upload_file", upload_file)

    chat_service = _FakeChatService()
    content = await save_code_execution_artifact(
        chat_service=chat_service,  # type: ignore[arg-type]
        file=_make_annotation("notes.txt"),
        file_bytes=b"hello",
    )

    assert content.id == "cont-bytes"
    upload_file.assert_not_called()
    chat_service.upload_to_chat_from_bytes_async.assert_awaited_once()
    _, kwargs = chat_service.upload_to_chat_from_bytes_async.await_args
    assert kwargs["mime_type"] == "text/plain"
    assert kwargs["content"] == b"hello"
