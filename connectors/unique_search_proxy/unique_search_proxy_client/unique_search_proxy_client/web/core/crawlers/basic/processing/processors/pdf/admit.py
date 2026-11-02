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
) -> PdfAdmissionError | None:
    """Return an admission error, or None when the body may be scanned/extracted.

    Download size is enforced by the shared HTTP response cap, not here.
    """
    normalized = (media_type or "").strip().lower()
    if normalized != "application/pdf":
        return PdfAdmissionError(
            code="PDF_UNSUPPORTED",
            message=f"Expected application/pdf, got {normalized or 'unknown'}",
        )
    if not body.startswith(PDF_MAGIC):
        return PdfAdmissionError(
            code="PDF_UNSUPPORTED",
            message="Response body is not a PDF (missing %PDF- header)",
        )
    return None


__all__ = ["PDF_MAGIC", "PdfAdmissionError", "admit_pdf_bytes"]
