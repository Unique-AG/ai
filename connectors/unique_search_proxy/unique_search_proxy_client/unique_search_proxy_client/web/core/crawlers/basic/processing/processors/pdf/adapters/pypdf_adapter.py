"""pypdf (BSD-3-Clause) text-layer extractor adapter."""

from __future__ import annotations

import asyncio
from pathlib import Path

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.adapters.pypdf_text import (
    extract_text_layer,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    extraction_result_from_payload,
)


def _extract_sync(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    if limits.ocr_enabled:
        return ExtractionResult(
            outcome=ExtractionOutcome.UNSUPPORTED,
            reason="OCR is disabled for Search Proxy PDF extraction",
            adapter_name="pypdf",
        )

    payload = extract_text_layer(
        str(path),
        max_pages=limits.max_pages,
        max_page_chars=limits.max_page_chars,
        max_document_chars=limits.max_document_chars,
    )
    return extraction_result_from_payload(payload, adapter_name="pypdf")


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
