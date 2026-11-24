from __future__ import annotations

from pathlib import Path
from typing import Protocol

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    PageChunk,
)


class PdfExtractor(Protocol):
    """Library-neutral PDF text-layer extractor."""

    @property
    def name(self) -> str: ...

    async def extract(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult: ...


class UnconfiguredPdfExtractor:
    """Default extractor until a licensed adapter is selected."""

    @property
    def name(self) -> str:
        return "unconfigured"

    async def extract(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult:
        del path, limits
        return ExtractionResult(
            outcome=ExtractionOutcome.FAILED,
            reason="PDF extractor is not configured",
            adapter_name=self.name,
        )


class FakePdfExtractor:
    """Test double that returns a predetermined extraction result."""

    def __init__(
        self,
        *,
        result: ExtractionResult | None = None,
        name: str = "fake",
    ) -> None:
        self._result = result or ExtractionResult(
            outcome=ExtractionOutcome.EXTRACTED,
            chunks=(PageChunk(page_number=1, text="# Fake"),),
            total_page_count=1,
            adapter_name=name,
        )
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def extract(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult:
        del path, limits
        return self._result


__all__ = [
    "FakePdfExtractor",
    "PdfExtractor",
    "UnconfiguredPdfExtractor",
]
