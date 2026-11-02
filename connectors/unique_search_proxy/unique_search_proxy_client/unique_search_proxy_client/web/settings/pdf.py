from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings

PDF_ENV_PREFIX = "PDF_"
PdfScanPolicySetting = Literal["disabled", "required"]


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
    max_document_hold_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    max_document_hold_documents: int = Field(default=16, ge=1)
    document_hold_ttl_seconds: float = Field(default=120.0, gt=0)
    document_hold_base_url: str = Field(
        default="http://127.0.0.1:2349",
        description=(
            "Base URL of this pod advertised in documentHandle.downloadUrl "
            "(path /v1/document-holds/{id} is appended)"
        ),
    )


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
