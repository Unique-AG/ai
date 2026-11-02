from __future__ import annotations

from dataclasses import dataclass

PDF_MAGIC = b"%PDF-"


@dataclass(frozen=True, slots=True)
class PdfAdmissionError:
    code: str
    message: str


def admit_pdf_bytes(
    body: bytes,
    *,
    media_type: str | None,
    max_bytes: int,
) -> PdfAdmissionError | None:
    """Return an admission error, or None when the body may be scanned/extracted."""
    normalized = (media_type or "").strip().lower()
    if normalized != "application/pdf":
        return PdfAdmissionError(
            code="PDF_UNSUPPORTED",
            message=f"Expected application/pdf, got {normalized or 'unknown'}",
        )
    if len(body) > max_bytes:
        return PdfAdmissionError(
            code="PDF_LIMIT_EXCEEDED",
            message=f"PDF exceeds maximum size of {max_bytes} bytes",
        )
    if not body.startswith(PDF_MAGIC):
        return PdfAdmissionError(
            code="PDF_UNSUPPORTED",
            message="Response body is not a PDF (missing %PDF- header)",
        )
    return None


__all__ = ["PDF_MAGIC", "PdfAdmissionError", "admit_pdf_bytes"]
