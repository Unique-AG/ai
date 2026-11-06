from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings

PDF_ENV_PREFIX = "PDF_"
_BYTES_PER_MB = 1024 * 1024


@helm_settings(
    title="PDF Processing",
    helm_key="pdfProcessing",
    kind="internal",
    gated=False,
    egress=None,
    env_prefix=PDF_ENV_PREFIX,
)
class PdfSettings(BaseSettings):
    """Deployment settings for PDF text extraction."""

    extractor: str = Field(
        default="pypdf",
        description=(
            "Extractor adapter id. Default is the BSD-licensed pypdf adapter. "
            "Use fake for tests, or none/off to disable extraction."
        ),
    )
    max_pdf_pages: int = Field(
        default=100,
        ge=1,
        description=(
            "Maximum number of pages to extract into the crawl response; "
            "longer PDFs are returned truncated"
        ),
    )
    max_extracted_chars: int = Field(
        default=100_000,
        ge=1,
        description=(
            "Total character budget for an extracted PDF; "
            "longer text is returned truncated"
        ),
    )
    extraction_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        description=(
            "Wall-clock limit for reading one PDF, also capped by the crawl "
            "request timeout; the extraction process is killed when it is reached"
        ),
    )
    max_extraction_memory_mb: int = Field(
        default=512,
        ge=128,
        description="Address-space limit (MiB) of the process that reads one PDF",
    )
    max_concurrent_extractions: int = Field(
        default=1,
        ge=1,
        description=(
            "PDFs read at the same time per worker process; further PDFs wait "
            "for a free slot within the request deadline"
        ),
    )

    @property
    def max_extraction_memory_bytes(self) -> int:
        return self.max_extraction_memory_mb * _BYTES_PER_MB


def get_pdf_settings() -> PdfSettings:
    return get_settings(PdfSettings, env_prefix=PDF_ENV_PREFIX)


pdf_settings: PdfSettings = get_pdf_settings()

__all__ = [
    "PDF_ENV_PREFIX",
    "PdfSettings",
    "get_pdf_settings",
    "pdf_settings",
]
