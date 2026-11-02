from __future__ import annotations

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.adapters.pypdf_adapter import (
    PyPdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.extractor import (
    FakePdfExtractor,
    PdfExtractor,
    UnconfiguredPdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.hold import (
    PdfDocumentHoldStore,
    PdfHoldSettings,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.process import (
    PdfProcessor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.runner import (
    InProcessExtractionRunner,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.scanner import (
    DocumentScanner,
    UnconfiguredDocumentScanner,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ScanPolicy,
)
from unique_search_proxy_client.web.settings.pdf import PdfSettings, pdf_settings

_HOLD_STORE: PdfDocumentHoldStore | None = None
_PDF_PROCESSOR: PdfProcessor | None = None


def _scan_policy_from_settings(settings: PdfSettings) -> ScanPolicy:
    return ScanPolicy(settings.scan_policy)


def build_pdf_extractor(settings: PdfSettings) -> PdfExtractor:
    name = settings.extractor.strip().lower()
    if name in {"none", "unconfigured", "off"}:
        return UnconfiguredPdfExtractor()
    if name == "fake":
        return FakePdfExtractor()
    if name in {"", "pypdf", "default"}:
        return PyPdfExtractor()
    return PyPdfExtractor()


def build_document_scanner(_settings: PdfSettings) -> DocumentScanner:
    return UnconfiguredDocumentScanner()


def get_pdf_hold_store(settings: PdfSettings | None = None) -> PdfDocumentHoldStore:
    global _HOLD_STORE
    if _HOLD_STORE is None:
        cfg = settings or pdf_settings
        _HOLD_STORE = PdfDocumentHoldStore(
            PdfHoldSettings(
                max_held_pdf_bytes=cfg.max_held_pdf_bytes,
                max_held_pdf_documents=cfg.max_held_pdf_documents,
                pdf_hold_ttl_seconds=cfg.pdf_hold_ttl_seconds,
                internal_base_url=cfg.internal_base_url,
            )
        )
    return _HOLD_STORE


def get_pdf_processor(settings: PdfSettings | None = None) -> PdfProcessor:
    global _PDF_PROCESSOR
    if _PDF_PROCESSOR is None:
        cfg = settings or pdf_settings
        extractor = build_pdf_extractor(cfg)
        _PDF_PROCESSOR = PdfProcessor(
            extractor=extractor,
            scanner=build_document_scanner(cfg),
            runner=InProcessExtractionRunner(extractor),
            hold_store=get_pdf_hold_store(cfg),
            scan_policy=_scan_policy_from_settings(cfg),
        )
    return _PDF_PROCESSOR


def reset_pdf_wiring_for_tests() -> None:
    """Clear process-local singletons between tests."""
    global _HOLD_STORE, _PDF_PROCESSOR
    _HOLD_STORE = None
    _PDF_PROCESSOR = None


__all__ = [
    "build_document_scanner",
    "build_pdf_extractor",
    "get_pdf_hold_store",
    "get_pdf_processor",
    "reset_pdf_wiring_for_tests",
]
