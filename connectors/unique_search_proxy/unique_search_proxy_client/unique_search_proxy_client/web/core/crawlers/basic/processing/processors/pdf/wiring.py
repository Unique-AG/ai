from __future__ import annotations

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.adapters.pypdf_adapter import (
    PyPdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.extractor import (
    FakePdfExtractor,
    PdfExtractor,
    UnconfiguredPdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.process import (
    PdfProcessor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.runner import (
    ExtractionRunner,
    InProcessExtractionRunner,
    SubprocessExtractionRunner,
)
from unique_search_proxy_client.web.settings.pdf import PdfSettings, pdf_settings

_PDF_PROCESSOR: PdfProcessor | None = None


def build_pdf_extractor(settings: PdfSettings) -> PdfExtractor:
    name = settings.extractor.strip().lower()
    if name in {"none", "unconfigured", "off"}:
        return UnconfiguredPdfExtractor()
    if name == "fake":
        return FakePdfExtractor()
    if name in {"", "pypdf", "default"}:
        return PyPdfExtractor()
    return PyPdfExtractor()


def build_extraction_runner(
    extractor: PdfExtractor,
    settings: PdfSettings,
) -> ExtractionRunner:
    """Run pypdf in a separate, limited process; other extractors in-process."""
    if isinstance(extractor, PyPdfExtractor):
        return SubprocessExtractionRunner(
            max_concurrent=settings.max_concurrent_extractions,
            max_memory_bytes=settings.max_extraction_memory_bytes,
        )
    return InProcessExtractionRunner(extractor)


def get_pdf_processor(settings: PdfSettings | None = None) -> PdfProcessor:
    global _PDF_PROCESSOR
    if _PDF_PROCESSOR is None:
        cfg = settings or pdf_settings
        extractor = build_pdf_extractor(cfg)
        _PDF_PROCESSOR = PdfProcessor(
            extractor=extractor,
            runner=build_extraction_runner(extractor, cfg),
        )
    return _PDF_PROCESSOR


def reset_pdf_wiring_for_tests() -> None:
    """Clear process-local singletons between tests."""
    global _PDF_PROCESSOR
    _PDF_PROCESSOR = None


__all__ = [
    "build_extraction_runner",
    "build_pdf_extractor",
    "get_pdf_processor",
    "reset_pdf_wiring_for_tests",
]
