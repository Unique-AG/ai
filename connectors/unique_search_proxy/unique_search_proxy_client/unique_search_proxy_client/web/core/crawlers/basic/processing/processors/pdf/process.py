from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from unique_search_proxy_core.schema import (
    CrawlUrlResult,
    PdfDocumentHandle,
    ProxyErrorCode,
)

from unique_search_proxy_client.web.core.crawlers.basic.processing.errors import (
    ContentProcessingError,
    ContentProcessingTimeoutError,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.admit import (
    admit_pdf_bytes,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.extractor import (
    PdfExtractor,
    UnconfiguredPdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.hold import (
    PdfDocumentHoldStore,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.runner import (
    ExtractionRunner,
    InProcessExtractionRunner,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.scanner import (
    DocumentScanner,
    UnconfiguredDocumentScanner,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    PageChunk,
    ScanPolicy,
    ScanVerdict,
)
from unique_search_proxy_client.web.core.provider_response import crawl_upstream_error

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PdfProcessingLimits:
    max_pdf_bytes: int
    max_inline_pdf_bytes: int
    max_pdf_pages: int
    max_pdf_page_chars: int
    max_pdf_document_chars: int
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class PdfProcessingOutcome:
    content: str | None = None
    document_handle: PdfDocumentHandle | None = None
    document_token: str | None = None
    error_result: CrawlUrlResult | None = None


def join_page_chunks(chunks: tuple[PageChunk, ...]) -> str:
    return "\n\n".join(chunk.text for chunk in chunks if chunk.text)


def _map_extraction_error(
    url: str,
    result: ExtractionResult,
) -> CrawlUrlResult:
    if result.outcome is ExtractionOutcome.UNSUPPORTED:
        return crawl_upstream_error(
            url,
            result.reason or "PDF is unsupported",
            content_type="application/pdf",
            code=ProxyErrorCode.PDF_UNSUPPORTED.value,
            raw=None,
        )
    return crawl_upstream_error(
        url,
        result.reason or "PDF extraction failed",
        content_type="application/pdf",
        code=ProxyErrorCode.UPSTREAM_ERROR.value,
        raw=None,
    )


class PdfProcessor:
    """Admit, scan, extract or hold a PDF under configured limits."""

    def __init__(
        self,
        *,
        extractor: PdfExtractor | None = None,
        scanner: DocumentScanner | None = None,
        runner: ExtractionRunner | None = None,
        hold_store: PdfDocumentHoldStore | None = None,
        scan_policy: ScanPolicy = ScanPolicy.DISABLED,
    ) -> None:
        self._extractor = extractor or UnconfiguredPdfExtractor()
        self._scanner = scanner or UnconfiguredDocumentScanner()
        self._runner = runner or InProcessExtractionRunner(self._extractor)
        self._hold_store = hold_store or PdfDocumentHoldStore()
        self._scan_policy = scan_policy

    @property
    def hold_store(self) -> PdfDocumentHoldStore:
        return self._hold_store

    async def process(
        self,
        body: bytes,
        *,
        url: str,
        media_type: str | None,
        limits: PdfProcessingLimits,
    ) -> PdfProcessingOutcome:
        admission_error = admit_pdf_bytes(
            body,
            media_type=media_type,
            max_bytes=limits.max_pdf_bytes,
        )
        if admission_error is not None:
            code = (
                ProxyErrorCode.PDF_LIMIT_EXCEEDED.value
                if admission_error.code == "PDF_LIMIT_EXCEEDED"
                else ProxyErrorCode.PDF_UNSUPPORTED.value
            )
            return PdfProcessingOutcome(
                error_result=crawl_upstream_error(
                    url,
                    admission_error.message,
                    content_type="application/pdf",
                    code=code,
                    raw=None,
                )
            )

        if isinstance(self._extractor, UnconfiguredPdfExtractor):
            return PdfProcessingOutcome(
                error_result=crawl_upstream_error(
                    url,
                    "PDF extractor is not configured",
                    content_type="application/pdf",
                    code=ProxyErrorCode.UPSTREAM_ERROR.value,
                    raw=None,
                )
            )

        with tempfile.TemporaryDirectory(prefix="usp-pdf-") as scratch_dir:
            path = Path(scratch_dir) / "document.pdf"
            path.write_bytes(body)

            scan = await self._scanner.scan(path, timeout=limits.timeout_seconds)
            if scan.verdict is ScanVerdict.MALICIOUS:
                _LOGGER.warning(
                    "PDF rejected by scanner=%s verdict=malicious",
                    scan.scanner_name,
                )
                return PdfProcessingOutcome(
                    error_result=crawl_upstream_error(
                        url,
                        scan.reason or "PDF rejected by malware scanner",
                        content_type="application/pdf",
                        code=ProxyErrorCode.PDF_REJECTED.value,
                        raw=None,
                    )
                )
            if scan.verdict is ScanVerdict.UNAVAILABLE:
                if self._scan_policy is ScanPolicy.REQUIRED:
                    return PdfProcessingOutcome(
                        error_result=crawl_upstream_error(
                            url,
                            scan.reason or "PDF scanner unavailable",
                            content_type="application/pdf",
                            code=ProxyErrorCode.PDF_REJECTED.value,
                            raw=None,
                        )
                    )
                _LOGGER.info(
                    "PDF scan skipped scanner=%s policy=disabled",
                    scan.scanner_name,
                )

            if len(body) > limits.max_inline_pdf_bytes:
                handle, token = self._hold_store.hold(body)
                _LOGGER.info(
                    "PDF held for internal download document_id=%s byte_size=%s",
                    handle.document_id,
                    handle.byte_size,
                )
                return PdfProcessingOutcome(
                    document_handle=handle,
                    document_token=token,
                )

            extraction_limits = ExtractionLimits(
                max_pages=limits.max_pdf_pages,
                max_page_chars=limits.max_pdf_page_chars,
                max_document_chars=limits.max_pdf_document_chars,
                timeout_seconds=limits.timeout_seconds,
                ocr_enabled=False,
            )
            try:
                result = await self._runner.run(path, extraction_limits)
            except TimeoutError as exc:
                raise ContentProcessingTimeoutError(
                    f"PDF extraction timed out after {limits.timeout_seconds}s",
                ) from exc
            except Exception as exc:
                raise ContentProcessingError(f"PDF extraction failed: {exc}") from exc

            if result.outcome in {
                ExtractionOutcome.UNSUPPORTED,
                ExtractionOutcome.FAILED,
            }:
                return PdfProcessingOutcome(
                    error_result=_map_extraction_error(url, result)
                )

            if (
                result.total_page_count is not None
                and result.total_page_count > limits.max_pdf_pages
            ):
                handle, token = self._hold_store.hold(
                    body,
                    page_count=result.total_page_count,
                )
                return PdfProcessingOutcome(
                    document_handle=handle,
                    document_token=token,
                )

            content = join_page_chunks(result.chunks)
            if len(content) > limits.max_pdf_document_chars:
                return PdfProcessingOutcome(
                    error_result=crawl_upstream_error(
                        url,
                        "PDF extracted content exceeds document character limit",
                        content_type="application/pdf",
                        code=ProxyErrorCode.PDF_LIMIT_EXCEEDED.value,
                        raw=None,
                    )
                )
            return PdfProcessingOutcome(content=content)


__all__ = [
    "PdfProcessingLimits",
    "PdfProcessingOutcome",
    "PdfProcessor",
    "join_page_chunks",
]
