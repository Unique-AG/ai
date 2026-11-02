from __future__ import annotations

import pytest
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf import (
    FakeDocumentScanner,
    FakePdfExtractor,
    InProcessExtractionRunner,
    PdfDocumentHoldStore,
    PdfHoldSettings,
    PdfProcessingLimits,
    PdfProcessor,
    UnconfiguredPdfExtractor,
    admit_pdf_bytes,
    join_page_chunks,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    PageChunk,
    ScanPolicy,
    ScanVerdict,
)

_PDF_BYTES = b"%PDF-1.4\n%content"


def _limits(**overrides: object) -> PdfProcessingLimits:
    base = PdfProcessingLimits(
        max_pdf_bytes=10_000,
        max_inline_pdf_bytes=5_000,
        max_pdf_pages=50,
        max_pdf_page_chars=20_000,
        max_pdf_document_chars=100_000,
        timeout_seconds=5.0,
    )
    if not overrides:
        return base
    data = {
        "max_pdf_bytes": base.max_pdf_bytes,
        "max_inline_pdf_bytes": base.max_inline_pdf_bytes,
        "max_pdf_pages": base.max_pdf_pages,
        "max_pdf_page_chars": base.max_pdf_page_chars,
        "max_pdf_document_chars": base.max_pdf_document_chars,
        "timeout_seconds": base.timeout_seconds,
    }
    data.update(overrides)
    return PdfProcessingLimits(**data)  # type: ignore[arg-type]


@pytest.mark.ai
def test_admit_pdf_bytes__rejects_missing_magic() -> None:
    """
    Purpose: Verify non-PDF payloads fail admission.
    Why this matters: MIME alone is not enough to trust a download.
    Setup summary: Pass a text body with application/pdf and expect an error.
    """
    error = admit_pdf_bytes(
        b"not-a-pdf",
        media_type="application/pdf",
        max_bytes=1000,
    )
    assert error is not None
    assert error.code == "PDF_UNSUPPORTED"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__extracts_with_fake_adapter() -> None:
    """
    Purpose: Verify PdfProcessor joins fake extractor chunks into Markdown.
    Why this matters: The crawler must depend only on the extractor contract.
    Setup summary: Wire FakePdfExtractor/FakeDocumentScanner and process a PDF.
    """
    extractor = FakePdfExtractor(
        result=ExtractionResult(
            outcome=ExtractionOutcome.EXTRACTED,
            chunks=(
                PageChunk(page_number=1, text="# Title"),
                PageChunk(page_number=2, text="Body"),
            ),
            total_page_count=2,
            adapter_name="fake",
        )
    )
    processor = PdfProcessor(
        extractor=extractor,
        scanner=FakeDocumentScanner(verdict=ScanVerdict.CLEAN),
        runner=InProcessExtractionRunner(extractor),
        scan_policy=ScanPolicy.DISABLED,
    )
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/doc.pdf",
        media_type="application/pdf",
        limits=_limits(),
    )
    assert outcome.error_result is None
    assert outcome.content == "# Title\n\nBody"
    assert outcome.document_handle is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pypdf_extractor__opens_real_pdf() -> None:
    """
    Purpose: Verify the default pypdf adapter parses a real PDF without licensing gates.
    Why this matters: Production extraction must work with a permissive open-source library.
    Setup summary: Write a one-page PDF with pypdf and extract it through PyPdfExtractor.
    """
    from io import BytesIO
    from pathlib import Path
    import tempfile

    from pypdf import PdfWriter

    from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.adapters.pypdf_adapter import (
        PyPdfExtractor,
    )

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)

    with tempfile.TemporaryDirectory(prefix="usp-pypdf-") as scratch:
        path = Path(scratch) / "sample.pdf"
        path.write_bytes(buffer.getvalue())
        result = await PyPdfExtractor().extract(
            path,
            ExtractionLimits(
                max_pages=50,
                max_page_chars=20_000,
                max_document_chars=100_000,
                timeout_seconds=5.0,
                ocr_enabled=False,
            ),
        )

    assert result.adapter_name == "pypdf"
    assert result.outcome is ExtractionOutcome.EMPTY
    assert result.total_page_count == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__unconfigured_extractor_fails_closed() -> None:
    """
    Purpose: Verify enabling PDF without an extractor returns a typed failure.
    Why this matters: Callers must not treat unconfigured extraction as success.
    Setup summary: Use UnconfiguredPdfExtractor and assert an upstream error.
    """
    processor = PdfProcessor(extractor=UnconfiguredPdfExtractor())
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/doc.pdf",
        media_type="application/pdf",
        limits=_limits(),
    )
    assert outcome.error_result is not None
    assert outcome.error_result.error is not None
    assert outcome.error_result.error.code == ProxyErrorCode.UPSTREAM_ERROR.value


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__required_scanner_rejects_unavailable() -> None:
    """
    Purpose: Verify REQUIRED scan policy fails when the scanner is unavailable.
    Why this matters: Fail-closed scanning must block extraction when configured.
    Setup summary: Use an unavailable fake scanner with ScanPolicy.REQUIRED.
    """
    processor = PdfProcessor(
        extractor=FakePdfExtractor(),
        scanner=FakeDocumentScanner(verdict=ScanVerdict.UNAVAILABLE),
        scan_policy=ScanPolicy.REQUIRED,
    )
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/doc.pdf",
        media_type="application/pdf",
        limits=_limits(),
    )
    assert outcome.error_result is not None
    assert outcome.error_result.error is not None
    assert outcome.error_result.error.code == ProxyErrorCode.PDF_REJECTED.value


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__holds_over_inline_budget() -> None:
    """
    Purpose: Verify oversized-but-admitted PDFs become document handles.
    Why this matters: Large files must leave the inline Markdown path.
    Setup summary: Set max_inline_pdf_bytes below body size and assert a hold.
    """
    hold_store = PdfDocumentHoldStore(
        PdfHoldSettings(internal_base_url="http://pod.local:2349")
    )
    processor = PdfProcessor(
        extractor=FakePdfExtractor(),
        scanner=FakeDocumentScanner(verdict=ScanVerdict.CLEAN),
        hold_store=hold_store,
    )
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/doc.pdf",
        media_type="application/pdf",
        limits=_limits(max_inline_pdf_bytes=4),
    )
    assert outcome.error_result is None
    assert outcome.content is None
    assert outcome.document_handle is not None
    assert outcome.document_handle.byte_size == len(_PDF_BYTES)
    consumed = hold_store.consume(
        outcome.document_handle.document_id,
        token=outcome.document_handle.token,
    )
    assert consumed == _PDF_BYTES


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__empty_extraction() -> None:
    """
    Purpose: Verify empty text-layer PDFs succeed with empty content.
    Why this matters: Scanned PDFs without OCR must not become hard errors.
    Setup summary: Return EMPTY from the fake extractor and assert content "".
    """
    empty = ExtractionResult(
        outcome=ExtractionOutcome.EMPTY,
        chunks=(),
        total_page_count=1,
        adapter_name="fake",
    )
    processor = PdfProcessor(
        extractor=FakePdfExtractor(result=empty),
        scanner=FakeDocumentScanner(),
        runner=InProcessExtractionRunner(FakePdfExtractor(result=empty)),
    )
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/scan.pdf",
        media_type="application/pdf",
        limits=_limits(),
    )
    assert outcome.error_result is None
    assert outcome.content == ""


@pytest.mark.ai
def test_join_page_chunks() -> None:
    """
    Purpose: Verify page chunks join with blank-line separators.
    Why this matters: Downstream prompts expect stable Markdown boundaries.
    Setup summary: Join two chunks and assert the separator.
    """
    assert (
        join_page_chunks(
            (
                PageChunk(page_number=1, text="A"),
                PageChunk(page_number=2, text="B"),
            )
        )
        == "A\n\nB"
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_in_process_runner__maps_timeout() -> None:
    """
    Purpose: Verify the in-process runner maps timeouts to FAILED.
    Why this matters: Native hangs must surface as typed extraction failures.
    Setup summary: Use a zero timeout against a fake extractor.
    """

    class SlowExtractor(FakePdfExtractor):
        async def extract(self, path, limits):  # type: ignore[no-untyped-def]
            import asyncio

            await asyncio.sleep(1)
            return await super().extract(path, limits)

    runner = InProcessExtractionRunner(SlowExtractor())
    result = await runner.run(
        path=__import__("pathlib").Path("."),
        limits=ExtractionLimits(
            max_pages=1,
            max_page_chars=10,
            max_document_chars=10,
            timeout_seconds=0.01,
        ),
    )
    assert result.outcome is ExtractionOutcome.FAILED
    assert result.reason is not None
    assert "timed out" in result.reason.lower()
