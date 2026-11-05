from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.extractor import (
    PdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
)


class ExtractionRunner(Protocol):
    """Runs an extractor under a wall-clock timeout."""

    async def run(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult: ...


class InProcessExtractionRunner:
    """In-process runner for pure-Python extractors such as pypdf."""

    def __init__(self, extractor: PdfExtractor) -> None:
        self._extractor = extractor

    async def run(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult:
        try:
            return await asyncio.wait_for(
                self._extractor.extract(path, limits),
                timeout=limits.timeout_seconds,
            )
        except TimeoutError:
            return ExtractionResult(
                outcome=ExtractionOutcome.FAILED,
                reason=(
                    f"PDF extraction timed out after {limits.timeout_seconds}s"
                ),
                adapter_name=self._extractor.name,
            )


__all__ = [
    "ExtractionRunner",
    "InProcessExtractionRunner",
]
