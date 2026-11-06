"""PDF extractor adapters. Swap implementations via ``PDF_EXTRACTOR`` settings."""

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.adapters.pypdf_adapter import (
    PyPdfExtractor,
)

__all__ = ["PyPdfExtractor"]
