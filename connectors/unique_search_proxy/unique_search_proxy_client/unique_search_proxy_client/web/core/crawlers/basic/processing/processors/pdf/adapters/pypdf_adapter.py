"""pypdf (BSD-3-Clause) text-layer extractor adapter."""

from __future__ import annotations

import asyncio
from pathlib import Path

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    PageChunk,
)


def _extract_sync(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    if limits.ocr_enabled:
        return ExtractionResult(
            outcome=ExtractionOutcome.UNSUPPORTED,
            reason="OCR is disabled for Search Proxy PDF extraction",
            adapter_name="pypdf",
        )

    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        return ExtractionResult(
            outcome=ExtractionOutcome.FAILED,
            reason=f"pypdf is not installed: {exc}",
            adapter_name="pypdf",
        )

    try:
        reader = PdfReader(str(path), strict=False)
    except PdfReadError:
        return ExtractionResult(
            outcome=ExtractionOutcome.UNSUPPORTED,
            reason="PDF could not be parsed",
            adapter_name="pypdf",
        )
    except Exception as exc:  # noqa: BLE001 - library boundary
        return ExtractionResult(
            outcome=ExtractionOutcome.FAILED,
            reason=f"Failed to open PDF: {exc.__class__.__name__}",
            adapter_name="pypdf",
        )

    if getattr(reader, "is_encrypted", False):
        try:
            unlocked = reader.decrypt("")
        except Exception:  # noqa: BLE001 - library boundary
            unlocked = 0
        if not unlocked:
            return ExtractionResult(
                outcome=ExtractionOutcome.UNSUPPORTED,
                reason="Encrypted PDFs are not supported",
                total_page_count=len(reader.pages),
                adapter_name="pypdf",
            )

    total_pages = len(reader.pages)
    chunks: list[PageChunk] = []
    total_chars = 0
    page_limit = min(total_pages, limits.max_pages)

    for index in range(page_limit):
        try:
            text = reader.pages[index].extract_text() or ""
        except Exception as exc:  # noqa: BLE001 - library boundary
            return ExtractionResult(
                outcome=ExtractionOutcome.FAILED,
                reason=f"Text extraction failed: {exc.__class__.__name__}",
                total_page_count=total_pages,
                adapter_name="pypdf",
            )

        truncated = False
        if len(text) > limits.max_page_chars:
            text = text[: limits.max_page_chars]
            truncated = True
        remaining = limits.max_document_chars - total_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[:remaining]
            truncated = True
        total_chars += len(text)
        chunks.append(
            PageChunk(
                page_number=index + 1,
                text=text,
                truncated=truncated,
            )
        )

    if not any(chunk.text.strip() for chunk in chunks):
        return ExtractionResult(
            outcome=ExtractionOutcome.EMPTY,
            chunks=tuple(chunks),
            total_page_count=total_pages,
            adapter_name="pypdf",
        )
    return ExtractionResult(
        outcome=ExtractionOutcome.EXTRACTED,
        chunks=tuple(chunks),
        total_page_count=total_pages,
        adapter_name="pypdf",
    )


class PyPdfExtractor:
    """PdfExtractor adapter backed by the BSD-licensed pypdf library."""

    @property
    def name(self) -> str:
        return "pypdf"

    async def extract(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult:
        return await asyncio.to_thread(_extract_sync, path, limits)


__all__ = ["PyPdfExtractor"]
