from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from unique_search_proxy_core.schema import (
    CrawlUrlResult,
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
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.runner import (
    ExtractionRunner,
    InProcessExtractionRunner,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    PageChunk,
)
from unique_search_proxy_client.web.core.provider_response import crawl_upstream_error
from unique_search_proxy_client.web.monitoring.metrics import (
    record_crawl_pdf_extraction,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PdfProcessingLimits:
    max_pdf_pages: int
    max_extracted_chars: int
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class PdfProcessingOutcome:
    content: str | None = None
    error_result: CrawlUrlResult | None = None


def join_page_chunks(chunks: tuple[PageChunk, ...]) -> str:
    return "\n\n".join(chunk.text for chunk in chunks if chunk.text)


def _truncation_note(*, last_page: int, total_pages: int, mid_page: bool) -> str:
    stop = "partway through page" if mid_page else "at page"
    return (
        "[This PDF is too large to include in full, so its text is truncated. "
        f"The text below stops {stop} {last_page} of {total_pages}.]"
    )


def _content_from_result(
    result: ExtractionResult,
    limits: PdfProcessingLimits,
) -> tuple[str, bool]:
    """Join pages within the character budget; return the content and whether it was cut."""
    content = join_page_chunks(result.chunks)
    mid_page = any(chunk.truncated for chunk in result.chunks)
    if len(content) > limits.max_extracted_chars:
        # The page separators can push the joined text past the budget.
        content = content[: limits.max_extracted_chars]
        mid_page = True
    total_pages = result.total_page_count or len(result.chunks)
    last_page = result.chunks[-1].page_number if result.chunks else 0
    if not mid_page and last_page >= total_pages:
        return content, False
    note = _truncation_note(
        last_page=last_page,
        total_pages=total_pages,
        mid_page=mid_page,
    )
    return f"{note}\n\n{content}", True


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
    """Admit and extract a PDF under configured limits."""

    def __init__(
        self,
        *,
        extractor: PdfExtractor | None = None,
        runner: ExtractionRunner | None = None,
    ) -> None:
        self._extractor = extractor or UnconfiguredPdfExtractor()
        self._runner = runner or InProcessExtractionRunner(self._extractor)

    async def process(
        self,
        body: bytes,
        *,
        url: str,
        media_type: str | None,
        limits: PdfProcessingLimits,
    ) -> PdfProcessingOutcome:
        admission_error = admit_pdf_bytes(body, media_type=media_type)
        if admission_error is not None:
            record_crawl_pdf_extraction("not_pdf", 0.0)
            return PdfProcessingOutcome(
                error_result=crawl_upstream_error(
                    url,
                    admission_error.message,
                    content_type="application/pdf",
                    code=ProxyErrorCode.PDF_UNSUPPORTED.value,
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

            extraction_limits = ExtractionLimits(
                max_pages=limits.max_pdf_pages,
                max_page_chars=limits.max_extracted_chars,
                max_document_chars=limits.max_extracted_chars,
                timeout_seconds=limits.timeout_seconds,
                ocr_enabled=False,
            )
            started = time.monotonic()
            try:
                result = await self._runner.run(path, extraction_limits)
            except TimeoutError as exc:
                record_crawl_pdf_extraction("timeout", time.monotonic() - started)
                _LOGGER.warning(
                    "PDF extraction timed out after %ss", limits.timeout_seconds
                )
                raise ContentProcessingTimeoutError(
                    f"PDF extraction timed out after {limits.timeout_seconds}s",
                ) from exc
            except asyncio.CancelledError:
                record_crawl_pdf_extraction("cancelled", time.monotonic() - started)
                raise
            except Exception as exc:
                record_crawl_pdf_extraction("failed", time.monotonic() - started)
                _LOGGER.warning(
                    "PDF extraction failed error_type=%s",
                    type(exc).__name__,
                    exc_info=exc,
                )
                raise ContentProcessingError(f"PDF extraction failed: {exc}") from exc
            duration = time.monotonic() - started

            if result.outcome in {
                ExtractionOutcome.UNSUPPORTED,
                ExtractionOutcome.FAILED,
            }:
                record_crawl_pdf_extraction(result.outcome.value, duration)
                _LOGGER.warning(
                    "PDF extraction %s reason=%s", result.outcome.value, result.reason
                )
                return PdfProcessingOutcome(
                    error_result=_map_extraction_error(url, result)
                )

            if result.outcome is ExtractionOutcome.EMPTY:
                record_crawl_pdf_extraction("empty", duration, result.total_page_count)
                return PdfProcessingOutcome(content=join_page_chunks(result.chunks))

            content, truncated = _content_from_result(result, limits)
            record_crawl_pdf_extraction(
                "truncated" if truncated else "extracted",
                duration,
                result.total_page_count,
            )
            return PdfProcessingOutcome(content=content)


__all__ = [
    "PdfProcessingLimits",
    "PdfProcessingOutcome",
    "PdfProcessor",
    "join_page_chunks",
]
