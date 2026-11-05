from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings

PDF_ENV_PREFIX = "PDF_"
PdfScanPolicySetting = Literal["disabled", "required"]
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
    """Deployment settings for PDF scanning, extraction, and in-memory holds."""

    scan_policy: PdfScanPolicySetting = Field(
        default="disabled",
        description=(
            "disabled: continue when the scanner is unavailable; "
            "required: reject the PDF when scanning cannot run"
        ),
    )
    extractor: str = Field(
        default="pypdf",
        description=(
            "Extractor adapter id. Default is the BSD-licensed pypdf adapter. "
            "Use fake for tests, or none/off to disable extraction."
        ),
    )
    max_inline_pdf_mb: int = Field(
        default=5,
        ge=1,
        description=(
            "PDFs at or below this size (MiB) are extracted inline into the crawl "
            "response. Larger PDFs fail with PDF_LIMIT_EXCEEDED (and may include a "
            "documentHandle for a separate download tool). Download size is capped "
            "by HTTP_CLIENT_MAX_RESPONSE_KIB, not by a PDF-specific limit."
        ),
    )
    max_pdf_pages: int = Field(
        default=100,
        ge=1,
        description="Maximum number of pages to extract into the crawl response",
    )
    max_extracted_chars: int = Field(
        default=100_000,
        ge=1,
        description="Total Markdown character budget for an extracted PDF",
    )
    max_document_hold_mb: int = Field(
        default=50,
        ge=1,
        description="Maximum total bytes (MiB) retained across in-memory document holds",
    )
    max_document_hold_documents: int = Field(
        default=16,
        ge=1,
        description="Maximum number of concurrent in-memory document holds on this pod",
    )
    document_hold_ttl_seconds: float = Field(
        default=120.0,
        gt=0,
        description="Time-to-live for a pod-local document hold before eviction",
    )
    document_hold_base_url: str = Field(
        default="http://127.0.0.1:2349",
        description=(
            "Base URL of this pod advertised in documentHandle.downloadUrl "
            "(path /v1/document-holds/{id} is appended)"
        ),
    )

    @property
    def max_inline_pdf_bytes(self) -> int:
        return self.max_inline_pdf_mb * _BYTES_PER_MB

    @property
    def max_document_hold_bytes(self) -> int:
        return self.max_document_hold_mb * _BYTES_PER_MB


def get_pdf_settings() -> PdfSettings:
    return get_settings(PdfSettings, env_prefix=PDF_ENV_PREFIX)


pdf_settings: PdfSettings = get_pdf_settings()

__all__ = [
    "PDF_ENV_PREFIX",
    "PdfScanPolicySetting",
    "PdfSettings",
    "get_pdf_settings",
    "pdf_settings",
]
